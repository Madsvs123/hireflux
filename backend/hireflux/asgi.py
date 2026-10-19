"""
ASGI config for HireFlux with Channels + JWT WebSocket auth.
"""
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hireflux.settings")

django_asgi_app = get_asgi_application()

from apps.core.routing import websocket_urlpatterns  # noqa: E402
from apps.core.ws_auth import JWTAuthMiddlewareStack  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
