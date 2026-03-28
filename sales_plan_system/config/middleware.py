import logging
import traceback
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

from core.errors import AppError

logger = logging.getLogger(__name__)


def ensure_request_id(request: HttpRequest) -> str:
    request_id = getattr(request, "request_id", None)
    if request_id:
        return request_id

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
    request.request_id = request_id
    return request_id


class RequestIDMiddleware:
    """Attach request id early so all downstream code can reuse it."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        ensure_request_id(request)
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response


class RBACCacheMiddleware:
    """Create request-scoped RBAC cache storage."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request._rbac_cache = {}
        return self.get_response(request)


class ExceptionHandlerMiddleware:
    """Convert application errors to a stable JSON response shape."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = ensure_request_id(request)
        try:
            response = self.get_response(request)
        except AppError as exc:
            self._log_app_error(request, exc, request_id)
            response = self._build_error_response(exc, request_id)
        except Exception as exc:  # pragma: no cover - defensive logging path
            self._log_unexpected_error(request, exc, request_id)
            response = self._build_unexpected_response(request_id)

        response["X-Request-ID"] = request_id
        return response

    def _log_app_error(self, request: HttpRequest, error: AppError, request_id: str) -> None:
        log_method = logger.error if error.status_code >= 500 else logger.warning
        log_method(
            "Application error",
            extra={
                "request_id": request_id,
                "path": request.path,
                "method": request.method,
                "user_id": getattr(getattr(request, "user", None), "pk", None),
                "error_code": error.code,
                "error_message": error.message,
                "error_details": error.details,
            },
        )

    def _log_unexpected_error(self, request: HttpRequest, error: Exception, request_id: str) -> None:
        logger.error(
            "Unexpected error: %s\n%s",
            error,
            traceback.format_exc(),
            extra={
                "request_id": request_id,
                "path": request.path,
                "method": request.method,
                "user_id": getattr(getattr(request, "user", None), "pk", None),
            },
        )

    def _build_error_response(self, error: AppError, request_id: str) -> JsonResponse:
        payload = error.to_dict()
        payload["error"]["request_id"] = request_id
        return JsonResponse(payload, status=error.status_code)

    def _build_unexpected_response(self, request_id: str) -> JsonResponse:
        return JsonResponse(
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "系统内部错误，请稍后重试",
                    "status": 500,
                    "request_id": request_id,
                },
            },
            status=500,
        )
