from django.shortcuts import render
from django.http import JsonResponse, HttpResponseNotFound


def health(request):
    """Health check endpoint for load balancers and monitoring."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return JsonResponse({'status': 'ok', 'service': 'legalv1'}, status=200)


def schema_view(request):
    """OpenAPI schema. Only served when DEBUG=True to avoid exposing API structure in production."""
    from django.conf import settings
    if not settings.DEBUG:
        return HttpResponseNotFound()
    from drf_spectacular.views import SpectacularAPIView
    return SpectacularAPIView.as_view()(request)


def swagger_ui_view(request):
    """Swagger UI. Only served when DEBUG=True."""
    from django.conf import settings
    if not settings.DEBUG:
        return HttpResponseNotFound()
    from drf_spectacular.views import SpectacularSwaggerView
    return SpectacularSwaggerView.as_view(url_name='schema')(request)
