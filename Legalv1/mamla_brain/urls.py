from django.urls import path

from . import views


urlpatterns = [
    path('v1/health/', views.health),
    path('v1/docs/upload/', views.upload_doc),
    path('v1/docs/', views.list_docs),
    path('v1/sessions/', views.create_session),
    path('v1/sessions/list/', views.list_sessions),
    path('v1/sessions/<str:session_id>/messages/', views.get_messages),
    path('v1/sessions/<str:session_id>/message/', views.send_message),
    path('v1/sessions/<str:session_id>/', views.delete_session),
    path('v1/case-companion/start/', views.start_case_companion),
    path('v1/case-companion/<str:session_id>/advise/', views.case_companion_advise),
    path('v1/admin/keys/', views.generate_admin_api_key),
    path('v1/usage/', views.usage_stats),
]
