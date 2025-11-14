from django.urls import include, path

from main import views

urlpatterns = [
    path("ads.txt", views.ads_txt, name="ads-txt"),
    path("robots.txt", views.robots_txt, name="robots-txt"),
    path("celery-progress/", include("celery_progress.urls"), name="celery-progress"),
    path("login", views.login, name="login"),
    path("expand", views.expand, name="expand"),
    path("playlist", views.playlist, name="playlist"),
    path("callback", views.callback, name="spotify-callback"),
    path("subscribers", views.add_subscriber, name="add_subscriber"),
    path("", views.index, name="home"),
]
