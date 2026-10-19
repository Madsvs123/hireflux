"""
JWT authentication middleware for Channels WebSockets.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(user_id):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        return User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Authenticate websocket connections via:
      - Query string ``?token=<access_jwt>``
      - Or ``Authorization: Bearer <access_jwt>`` header
    """

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["user"] = AnonymousUser()

        token = self._extract_token(scope)
        if token:
            try:
                access = AccessToken(token)
                user_id = access.get("user_id")
                if user_id:
                    scope["user"] = await _get_user(user_id)
            except Exception:  # noqa: BLE001
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @staticmethod
    def _extract_token(scope) -> str | None:
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        if "token" in params and params["token"]:
            return params["token"][0]

        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"").decode()
        if auth.startswith("Bearer "):
            return auth.split(" ", 1)[1].strip()
        return None


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
