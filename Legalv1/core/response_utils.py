"""Shared response helpers for consistent API responses."""
from django.http import JsonResponse


def error_response(message, status=400, detail=None):
    """Return a standard JSON error response."""
    payload = {"error": message}
    if detail is not None:
        payload["detail"] = detail
    return JsonResponse(payload, status=status)
