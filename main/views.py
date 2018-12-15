import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .tasks import generate_playlist
from django.views.decorators.http import require_POST
from main import oauth

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

def index(request):
    return render(request, 'playlist.html')
