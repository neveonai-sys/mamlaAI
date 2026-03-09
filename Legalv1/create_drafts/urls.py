from django.urls import path
from create_drafts import views

urlpatterns = [
    path('get-all-drafts/', views.get_available_drafts_list),
    path('draft-items', views.get_all_drafts_from_drafttype_folder),
    path('draft-fields/', views.fetch_required_fields_from_doc),
    path('submit-draft/', views.create_final_draft_and_send_pdf),
    path('get-saved-drafts/', views.get_saved_drafts),
    path('load-saved-draft/', views.load_saved_draft),
    path('auto-save/', views.auto_save),
    path('get-template/', views.fetch_pdftemplate_from_doc),
    path('get-updated-template/', views.update_template_with_suggestions),
]