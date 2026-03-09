from django.urls import path
from search_facility import views

urlpatterns = [
    path('index-documents/', views.index_documents),
    path('search-by-index', views.search_view),
    path('fetch-content/', views.fetch_content_by_drafttype_and_filename),
]

