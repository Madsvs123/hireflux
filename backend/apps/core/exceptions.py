"""
Unified API exception handling.
"""
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class HireFluxAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "error"
    default_detail = "An error occurred."

    def __init__(self, detail=None, code=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=detail, code=code)


class NotFoundError(HireFluxAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "not_found"
    default_detail = "Resource not found."


class ConflictError(HireFluxAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"
    default_detail = "Conflict with current state."


class ForbiddenError(HireFluxAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "forbidden"
    default_detail = "You do not have permission to perform this action."


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None
        return None

    payload = {
        "success": False,
        "error": {
            "code": getattr(exc, "default_code", None)
            or getattr(exc, "code", None)
            or "error",
            "message": _extract_message(response.data),
            "details": response.data if isinstance(response.data, dict) else {"detail": response.data},
        },
    }

    # Prefer explicit code from DRF exceptions
    if hasattr(exc, "get_codes"):
        codes = exc.get_codes()
        if isinstance(codes, str):
            payload["error"]["code"] = codes
        elif isinstance(codes, dict) and "detail" in codes:
            payload["error"]["code"] = codes["detail"]

    response.data = payload
    return response


def _extract_message(data):
    if data is None:
        return "An error occurred."
    if isinstance(data, str):
        return data
    if isinstance(data, list) and data:
        return str(data[0])
    if isinstance(data, dict):
        if "detail" in data:
            detail = data["detail"]
            if isinstance(detail, list):
                return str(detail[0])
            return str(detail)
        # First field error
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
            return f"{key}: {value}"
    return str(data)
