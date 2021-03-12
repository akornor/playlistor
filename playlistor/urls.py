from django.urls import path, include
from main import views

urlpatterns = [
    path("celery-progress/", include("celery_progress.urls"), name="celery-progress"),
    path("login", views.login, name="login"),
    path("expand", views.expand, name="expand"),
    path("playlist", views.playlist, name="playlist"),
    path("callback", views.callback, name="spotify-callback"),
    path("", views.index, name="home"),
]
