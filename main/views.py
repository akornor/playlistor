import json
import os
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from .tasks import generate_playlist
from django.views.decorators.http import require_POST
from main import oauth

TOKEN = os.path.join(settings.BASE_DIR, 'token.json')

def login(request):
    authorize_url = oauth.get_authorize_url()
    return redirect(authorize_url)

def callback(request):
    code = request.GET.get('code')
    if code is not None:
        oauth.get_access_token(code)
        return redirect('/')

@require_POST
def playlist(request):
    data = json.loads(request.body.decode('utf-8'))
    playlist = data.get('playlist')
    if playlist is not None:
        result = generate_playlist.delay(playlist)
        return JsonResponse({'task_id': result.task_id})
    return JsonResponse({'message': "playlist required in payload"})

def login_required(function=None, redirect_field_name=None, login_url=None):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: os.path.exists(TOKEN),
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


@login_required(login_url='/login')
def index(request):
    return render(request, 'playlist.html')
