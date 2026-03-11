from django.urls import path
from . import views

urlpatterns = [
    # REST-compatible aliases (used by new frontend)
    path('documents/', views.documents_list),
    path('documents/<str:doc_id>/', views.delete_document),
    path('documents/<str:doc_id>/file/', views.document_file),
    path('sessions/', views.sessions_list_v2),
    path('session_messages/', views.session_messages_v2),
    path('upload/', views.upload_file),
    path('create_session/', views.create_session_v2),
    path('query/', views.query_v2),

    # Documents
    path('docs/upload', views.upload_doc, name='rag_upload_doc'),
    path('docs', views.list_docs, name='rag_list_docs'),

    # Sessions
    path('sessions', views.create_session, name='rag_create_session'),
    path('sessions/list', views.list_sessions, name='rag_list_sessions'),
    path('sessions/<str:session_id>/messages', views.get_messages, name='rag_get_messages'),
    path('sessions/<str:session_id>/message', views.send_message, name='rag_send_message'),
    path('sessions/<str:session_id>/docs', views.modify_session_docs, name='rag_modify_session_docs'),
    path('sessions/<str:session_id>', views.delete_session, name='rag_delete_session'),
    path('rename_session/<str:session_id>', views.rename_session, name='rename_session'),

]
