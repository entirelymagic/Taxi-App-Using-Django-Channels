from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path
from trips.consumers import TaxiConsumer

from taxi.middleware import TokenAuthMiddlewareStack

application = ProtocolTypeRouter(
    {
        'http': get_asgi_application(),
        'websocket': TokenAuthMiddlewareStack(
            URLRouter(
                [
                    path('taxi/', TaxiConsumer.as_asgi()),
                ]
            )
        ),
    }
)
