import time
from datetime import datetime, UTC

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

APP_START_TIME = time.time()


@never_cache
@require_GET
def health_check(_request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "sales_plan_system",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


@never_cache
@require_GET
def readiness_check(_request):
    database = _check_database()
    healthy = database["status"] == "ok"

    return JsonResponse(
        {
            "status": "ok" if healthy else "unhealthy",
            "checks": {"database": database},
            "uptime_seconds": round(time.time() - APP_START_TIME, 2),
            "timestamp": datetime.now(UTC).isoformat(),
        },
        status=200 if healthy else 503,
    )


def _check_database() -> dict:
    try:
        started = time.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except DatabaseError as exc:
        return {"status": "error", "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive branch
        return {"status": "error", "error": f"Unexpected error: {exc}"}
