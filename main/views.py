import json
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
from main import oauth
from .tasks import generate_spotify_playlist, generate_applemusic_playlist
from .decorators import login_required
from .utils import get_redis_client, requests_retry_session
from .models import Playlist


def login(request):
    authorize_url = oauth.get_authorize_url()
    return redirect(authorize_url)


def callback(request):
    code = request.GET.get("code")
    if code is not None:
        oauth.get_access_token(code)
        return redirect(reverse("home"))
    else:
        return redirect(reverse("login"))


@require_POST
def playlist(request):
    """
    API endpoint to schedule generate_playlist tasks
    """
    data = json.loads(request.body.decode("utf-8"))
    playlist = data.get("playlist")
    platform = data.get("platform")
    if playlist is None:
        return JsonResponse({"message": "playlist required in payload"}, status=400)
    if platform is None:
        return JsonResponse({"message": "platform required in payload"}, status=400)
    if platform == "apple-music":
        token = request.headers.get("Music-User-Token")
        result = generate_applemusic_playlist.delay(playlist, token)
    elif platform == "spotify":
        result = generate_spotify_playlist.delay(playlist)
    else:
        return JsonResponse(
            {"message": f"platform {platform} not supported"}, status=400
        )
    return JsonResponse({"task_id": result.task_id})

@require_POST
def expand(request):
    data = json.loads(request.body.decode("utf-8"))
    url = data.get("url")
    session = requests_retry_session()
    try:
        response = session.head(url, allow_redirects=True)
        response.raise_for_status()
        return JsonResponse({"url": response.url})
    except Exception:
        return JsonResponse({"message": f"{url} not found."}, status=400)
    


@login_required(login_url="/login")
def index(request):
    redis_client = get_redis_client()
    count = int((redis_client.get("playlists") or 0))
    playlists = Playlist.objects.order_by('-created_at')[:5]
    return render(request, "index.html", {"playlists": playlists, "count": count})
