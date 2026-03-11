from django.urls import path
from ai_draft import views, test_views

# Authenticated endpoints (protected by auth middleware)
authenticated_urlpatterns = [
    # ── New REST-compatible endpoints (mamlaAI frontend) ──
    path('list/', views.list_drafts),
    path('initial_request/', views.initiate_drafting_session),
    path('section_edit/', views.section_edit),
    path('refine_section/', views.refine_section),
    path('export/', views.export_draft),
    # ── Legacy endpoints ──
    path('get-draft-count/', views.get_total_drafts),
    path('start_session', views.initiate_drafting_session),
    path('set_location', views.set_location),
    path('update_section', views.update_section),
    path('download_draft', views.download_draft),
    path('get_draft_sections', views.get_draft_sections),
    path('get_draft_single_section', views.get_draft_single_section),
    path('delete_section', views.delete_section),
    path('suggest_section', views.suggest_section),
    path('add_section', views.add_section),
    path('revert_to_original', views.revert_to_original),
    path('update_section_order', views.update_section_order),
    path('get_section_history', views.get_section_history),
    path('save_draft', views.save_draft),
    path('get_user_saved_drafts', views.get_user_saved_drafts),
    path('get_user_saved_drafts_v2', views.get_user_saved_drafts_v2),
    path('load_saved_draft', views.load_saved_draft),
    path('delete_saved_draft', views.delete_saved_draft),
    path('upload_template', views.upload_template),
    path('start_session_for_casedocument', views.create_drfatsession_by_casedocument),
    path('download_template', views.send_default_template_for_create_draft),
    path('get_draft_for', views.get_draft_for_draftsession_id),
    path('get_supported_languages', views.get_supported_languages),
]

# Test draft endpoints (no authentication required, rate limited)
test_urlpatterns = [
    path('test/hello/', test_views.test_hello, name='test_hello'),
    path('test/create/', test_views.create_test_draft, name='create_test_draft'),
    path('test/update/', test_views.update_test_section, name='update_test_section'),
    path('test/download/', test_views.download_test_draft, name='download_test_draft'),
    path('test/status/<uuid:session_id>/', test_views.test_draft_status, name='test_draft_status'),
    path('test/sections/<str:session_id>/', test_views.get_test_draft_sections, name='get_test_draft_sections'),
]

# Combine both URL patterns
urlpatterns = authenticated_urlpatterns + test_urlpatterns