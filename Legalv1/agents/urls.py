"""
agents/urls.py — URL routing for all agent endpoints.
All paths are under /api/agents/ (registered in Legalv1/urls.py).
"""
from django.urls import path
from . import views

urlpatterns = [
    path('case-intake/',    views.case_intake,    name='agent-case-intake'),
    path('document-intel/', views.document_intel,  name='agent-document-intel'),
    path('hearing-prep/',   views.hearing_prep,    name='agent-hearing-prep'),
    path('post-hearing/',   views.post_hearing,    name='agent-post-hearing'),
    path('draft-context/',  views.draft_context,   name='agent-draft-context'),
    path('case-closure/',   views.case_closure,    name='agent-case-closure'),
]
