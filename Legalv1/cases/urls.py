from django.urls import path
from cases import views

urlpatterns = [
    # ── Case CRUD ─────────────────────────────────────────────────────────────
    path('create/',                                   views.create_case),
    path('list/',                                     views.list_cases),
    path('<str:case_id>/',                            views.get_case),
    path('<str:case_id>/update/',                     views.update_case),
    path('<str:case_id>/close/',                      views.close_case),
    path('<str:case_id>/timeline/',                   views.get_timeline),

    # ── Hearing notes ─────────────────────────────────────────────────────────
    path('<str:case_id>/hearing-notes/',              views.create_hearing_note),
    path('<str:case_id>/hearing-notes/list/',         views.list_hearing_notes),
    path('<str:case_id>/hearing-notes/<str:note_id>/',        views.get_hearing_note),
    path('<str:case_id>/hearing-notes/<str:note_id>/update/', views.update_hearing_note),

    # ── Case notes ────────────────────────────────────────────────────────────
    path('<str:case_id>/notes/',                      views.create_case_note),
    path('<str:case_id>/notes/list/',                 views.list_case_notes),
    path('<str:case_id>/notes/<str:note_id>/update/', views.update_case_note),
    path('<str:case_id>/notes/<str:note_id>/delete/', views.delete_case_note),

    # ── Case tasks ────────────────────────────────────────────────────────────
    path('<str:case_id>/tasks/',                      views.create_case_task),
    path('<str:case_id>/tasks/list/',                 views.list_case_tasks),
    path('<str:case_id>/tasks/<str:task_id>/update/', views.update_case_task),
    path('<str:case_id>/tasks/<str:task_id>/delete/', views.delete_case_task),
]
