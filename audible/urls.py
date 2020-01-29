"""audible URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from main import views

urlpatterns = [
    path('celery-progress/', include('celery_progress.urls'), name="celery-progress"),
    path('login', views.login, name='login'),
    path('expand', views.expand, name="expand"),
    path('playlist', views.playlist, name="playlist"),
    path('callback', views.callback, name="spotify-callback"),
    path('', views.index, name="home"),
]
