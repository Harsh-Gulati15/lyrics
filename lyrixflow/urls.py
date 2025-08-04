from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'), # Homepage
    path('dashboard/', views.genre_dashboard_view, name='dashboard'),
    path('genre/<slug:genre_slug>/artists/', views.artist_selection_view, name='artist_selection'),
    path('chat/new/<str:artist_name>/', views.new_chat_view, name='new_chat'),
    path('chat/<str:rapper_name>/', views.chat_view, name='chat'),
    path('chat/session/<int:session_id>/', views.chat_session_view, name='chat_session'),
    path('generate_lyrics', views.generate_lyrics_api, name='generate_lyrics'),
    path('chat/delete/<int:session_id>/', views.delete_chat_view, name='delete_chat'),

]