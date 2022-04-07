import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework_simplejwt.tokens import AccessToken
from taxi.routing import application
from trips.models import Trip

TEST_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}


@database_sync_to_async
def create_user(username, password, group='rider'):
    # Create user.
    user = get_user_model().objects.create_user(username=username, password=password)

    # Create user group.
    user_group, _ = Group.objects.get_or_create(name=group)  # new
    user.groups.add(user_group)
    user.save()

    # Create access token.
    access = AccessToken.for_user(user)

    return user, access


@database_sync_to_async
def create_trip(
    pick_up_address='123 Main Street', drop_off_address='456 Piney Road', status='REQUESTED', rider=None, driver=None
):
    return Trip.objects.create(
        pick_up_address=pick_up_address,
        drop_off_address=drop_off_address,
        status=status,
        rider=rider,
        driver=driver,
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestWebSocket:
    async def test_can_connect_to_server(self, settings):
        _, access = await create_user('test.user@example.com', 'pAssw0rd')
        communicator = WebsocketCommunicator(application=application, path=f'/taxi/?token={access}')
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    async def test_can_send_and_receive_messages(self, settings):
        settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS
        communicator = WebsocketCommunicator(application=application, path='/taxi/')
        await communicator.connect()
        message = {
            'type': 'echo.message',
            'data': 'This is a test message.',
        }
        await communicator.send_json_to(message)
        response = await communicator.receive_json_from()
        assert response == message
        await communicator.disconnect()

    async def test_cannot_connect_to_socket(self, settings):
        settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS
        communicator = WebsocketCommunicator(application=application, path='/taxi/')
        connected, _ = await communicator.connect()
        assert connected is False
        await communicator.disconnect()

    async def test_join_driver_pool(self, settings):
        settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS
        _, access = await create_user('test.user@example.com', 'pAssw0rd', 'driver')
        communicator = WebsocketCommunicator(application=application, path=f'/taxi/?token={access}')
        await communicator.connect()
        message = {
            'type': 'echo.message',
            'data': 'This is a test message.',
        }
        channel_layer = get_channel_layer()
        await channel_layer.group_send('drivers', message=message)
        response = await communicator.receive_json_from()
        assert response == message
        await communicator.disconnect()

    async def test_request_trip(self, settings):
        settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS
        user, access = await create_user('test.user@example.com', 'pAssw0rd', 'rider')
        communicator = WebsocketCommunicator(application=application, path=f'/taxi/?token={access}')
        await communicator.connect()
        await communicator.send_json_to(
            {
                'type': 'create.trip',
                'data': {
                    'pick_up_address': '123 Main Street',
                    'drop_off_address': '456 Piney Road',
                    'rider': user.id,
                },
            }
        )
        response = await communicator.receive_json_from()
        response_data = response.get('data')
        assert response_data['id'] is not None
        assert response_data['pick_up_address'] == '123 Main Street'
        assert response_data['drop_off_address'] == '456 Piney Road'
        assert response_data['status'] == 'REQUESTED'
        assert response_data['rider']['username'] == user.username
        assert response_data['driver'] is None
        await communicator.disconnect()

    async def test_driver_alerted_on_request(self, settings):
        """A ride request should be broadcast to all drivers in the driver pool the moment it's sent."""
        settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS

        # Listen to the 'drivers' group test channel.
        channel_layer = get_channel_layer()
        await channel_layer.group_add(group='drivers', channel='test_channel')

        user, access = await create_user('test.user@example.com', 'pAssw0rd', 'rider')
        communicator = WebsocketCommunicator(application=application, path=f'/taxi/?token={access}')
        await communicator.connect()

        # Request a trip.
        await communicator.send_json_to(
            {
                'type': 'create.trip',
                'data': {
                    'pick_up_address': '123 Main Street',
                    'drop_off_address': '456 Piney Road',
                    'rider': user.id,
                },
            }
        )

        # Receive JSON message from server on test channel.
        response = await channel_layer.receive('test_channel')
        response_data = response.get('data')

        assert response_data['id'] is not None
        assert response_data['rider']['username'] == user.username
        assert response_data['driver'] is None

        await communicator.disconnect()

    async def test_create_trip_group(self, settings):
        settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS
        user, access = await create_user('test.user@example.com', 'pAssw0rd', 'rider')
        communicator = WebsocketCommunicator(application=application, path=f'/taxi/?token={access}')
        await communicator.connect()

        # Send a ride request.
        await communicator.send_json_to(
            {
                'type': 'create.trip',
                'data': {
                    'pick_up_address': '123 Main Street',
                    'drop_off_address': '456 Piney Road',
                    'rider': user.id,
                },
            }
        )
        response = await communicator.receive_json_from()
        response_data = response.get('data')

        # Send a message to the trip group.
        message = {
            'type': 'echo.message',
            'data': 'This is a test message.',
        }
        channel_layer = get_channel_layer()
        await channel_layer.group_send(response_data['id'], message=message)

        # Rider receives message.
        response = await communicator.receive_json_from()
        assert response == message

        await communicator.disconnect()

    async def test_join_trip_group_on_connect(self, settings):
        settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS
        user, access = await create_user('test.user@example.com', 'pAssw0rd', 'rider')
        trip = await create_trip(rider=user)
        communicator = WebsocketCommunicator(application=application, path=f'/taxi/?token={access}')
        await communicator.connect()

        # Send a message to the trip group.
        message = {
            'type': 'echo.message',
            'data': 'This is a test message.',
        }
        channel_layer = get_channel_layer()
        await channel_layer.group_send(f'{trip.id}', message=message)

        # Rider receives message.
        response = await communicator.receive_json_from()
        assert response == message

        await communicator.disconnect()
