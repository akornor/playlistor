import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .tasks import generate_spotify_playlist, generate_applemusic_playlist
from .decorators import login_required
from main import oauth
from .utils import redis_client

def login(request):
    authorize_url = oauth.get_authorize_url()
    return redirect(authorize_url)

def callback(request):
    code = request.GET.get('code')
    if code is not None:
        oauth.get_access_token(code)
        return redirect('/')
    else:
        return redirect('/login')

@require_POST
def playlist(request):
    """
    API endpoint to schedule generate_playlist tasks
    """
    data = json.loads(request.body.decode('utf-8'))
    playlist = data.get('playlist')
    if playlist is None:
        return JsonResponse({'message': "playlist required in payload"}, status=400)
    result = generate_applemusic_playlist.delay(playlist)
    return JsonResponse({'task_id': result.task_id})

@login_required(login_url='/login')
def index(request):
    count = redis_client.llen('playlists')
    playlists = redis_client.lrange('playlists', 0, 3)
    playlists = [ json.loads(playlist) for playlist in playlists ]
    return render(request, 'index.html', { "playlists": playlists, "count": count })
