import copy

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.db.models import Q

from trips.models import Trip
from trips.serializers import NestedTripSerializer, TripSerializer


class TaxiConsumer(AsyncJsonWebsocketConsumer):
    groups = ['test']

    @database_sync_to_async
    def _get_user_group(self, user):
        return user.groups.first().name

    @database_sync_to_async
    def _create_trip(self, data):
        serializer = TripSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.create(serializer.validated_data)

    @database_sync_to_async
    def _get_trip_data(self, trip):
        return NestedTripSerializer(trip).data

    @database_sync_to_async
    def _get_trip_ids(self, user):
        user_groups = user.groups.values_list('name', flat=True)
        if 'driver' in user_groups:
            trip_ids = user.trips_as_driver.exclude(status=Trip.COMPLETED).only('id').values_list('id', flat=True)
        elif "rider" in user_groups:
            trip_ids = user.trips_as_rider.exclude(status=Trip.COMPLETED).only('id').values_list('id', flat=True)
        return map(str, trip_ids)

    @database_sync_to_async
    def _update_trip(self, data):
        instance = Trip.objects.get(id=data.get('id'))
        serializer = TripSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.update(instance, serializer.validated_data)

    @database_sync_to_async
    def _check_if_trip_allowed(self):
        user = self.scope['user']
        user_group = user.groups.first().name
        # Check if there is an active trip and return an error if there is.
        if user_group == 'rider':
            if user.trips_as_rider.exclude(status=Trip.COMPLETED).exists():
                return self.send_json({'type': 'error', 'data': 'You already have an active trip.'})
        else:
            return self.send_json({'type': 'error', 'data': 'You are not a rider.'})
        return None

    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
        else:
            user_group = await self._get_user_group(user)
            if user_group == 'driver':
                await self.channel_layer.group_add(group='drivers', channel=self.channel_name)

            for trip_id in await self._get_trip_ids(user):
                await self.channel_layer.group_add(group=trip_id, channel=self.channel_name)
            await self.accept()

    async def create_trip(self, message):
        """allow only rider users who don't have an active trip to create a trip"""

        # Allow only rider users to create a trip
        active_trip_error_message = await self._check_if_trip_allowed()
        if active_trip_error_message:
            return await active_trip_error_message

        data = message.get('data')
        trip = await self._create_trip(data)
        trip_data = await self._get_trip_data(trip)

        # Send rider requests to all drivers.
        await self.channel_layer.group_send(
            group='drivers',
            message={'type': 'echo.message', 'data': trip_data},
        )
        # Add rider to trip group.
        await self.channel_layer.group_add(group=trip.id, channel=self.channel_name)

        await self.send_json({'type': 'echo.message', 'data': trip_data})
        
    # only add extra rider to trip group when rider desire this
    async def add_extra_rider(self, message):
        trip_id = message.get('data').get('trip_id')
        extra_user = message.get('data').get('extra_user')
        await self.channel_layer.group_add(group=trip_id, channel=extra_user)
        

    async def update_trip(self, message):
        data = message.get('data')
        trip = await self._update_trip(data)
        trip_id = f'{trip.id}'
        trip_data = await self._get_trip_data(trip)

        # Send update to rider.
        await self.channel_layer.group_send(
            group=trip_id,
            message={'type': 'echo.message', 'data': trip_data},
        )

        # Add driver to the trip group.
        await self.channel_layer.group_add(group=trip_id, channel=self.channel_name)

        # update the driver group to remove the trip from the group.
        trip_copy = copy.deepcopy(trip_data)
        trip_copy["driver"] = None
        await self.channel_layer.group_send(
            group='drivers',
            message={'type': 'echo.message', 'data': trip_copy},
        )

        await self.send_json({'type': 'echo.message', 'data': trip_data})

    async def cancel_trip(self, message):
        data = message.get('data')
        trip = await self._update_trip(data)
        trip_id = f'{trip.id}'
        trip_data = await self._get_trip_data(trip)

        # Send update to rider and driver.
        await self.channel_layer.group_send(
            group=trip_id,
            message={'type': 'echo.message', 'data': trip_data},
        )
        await self.channel_layer.group_send(
            group='drivers',
            message={'type': 'echo.message', 'data': trip_data},
        )
        # Remove driver and rider from the trip group.
        await self.channel_layer.group_discard(group=trip_id, channel=self.channel_name)
        # Send update to the drivers.

        await self.send_json({'type': 'echo.message', 'data': trip_data})

    async def disconnect(self, code):
        user = self.scope['user']

        if user.is_anonymous:
            await self.close()
        else:
            user_group = await self._get_user_group(user)
            if user_group == 'driver':
                await self.channel_layer.group_discard(group='drivers', channel=self.channel_name)

            for trip_id in await self._get_trip_ids(user):
                await self.channel_layer.group_discard(group=trip_id, channel=self.channel_name)
        await super().disconnect(code)

    async def echo_message(self, message):
        await self.send_json(message)

    async def receive_json(self, content, **kwargs):
        message_type = content.get('type')
        if message_type == 'create.trip':
            await self.create_trip(content)
        elif message_type == 'echo.message':
            await self.echo_message(content)
        elif message_type == 'update.trip':
            await self.update_trip(content)
        elif message_type == 'cancel.trip':
            await self.cancel_trip(content)
        elif message_type == 'add.extra.rider':
            await self.add_extra_rider(content)
