from django.urls import path

from . import views
from .orchestrator import views_v2


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

    # --- MamlaAI Chat (v2): unified multi-agent chat surface ---
    path('v2/sessions/', views_v2.create_session),
    path('v2/sessions/list/', views_v2.list_sessions),
    path('v2/usage-summary/', views_v2.usage_summary),
    path('v2/sessions/<str:session_id>/messages/', views_v2.get_messages),
    path('v2/sessions/<str:session_id>/upload/', views_v2.upload_doc),
    path('v2/sessions/<str:session_id>/chat/', views_v2.chat),
    path('v2/sessions/<str:session_id>/chat/stream/', views_v2.chat_stream),
    path('v2/sessions/<str:session_id>/', views_v2.session_detail),  # PATCH rename / DELETE
    # In-chat draft canvas (edit sections without leaving the chat)
    path('v2/drafts/<str:draft_session_id>/sections/', views_v2.get_draft_sections),
    path('v2/drafts/<str:draft_session_id>/section/', views_v2.update_draft_section),
]
