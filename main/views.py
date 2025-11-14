import json

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from jsonschema import validate
from jsonschema.exceptions import ValidationError as JsonSchemaValitadionError

from main import oauth_manager

from .decorators import login_required
from .models import Playlist, Subscriber
from .tasks import generate_applemusic_playlist, generate_spotify_playlist
from .utils import (
    get_redis_client,
    requests_retry_session,
    validate_apple_music_playlist_url,
    validate_spotify_playlist_url,
)


def login(request):
    authorize_url = oauth_manager.get_authorize_url()
    return redirect(authorize_url)


def callback(request):
    code = request.GET.get("code")
    if code is not None:
        oauth_manager.get_access_token(code)
        return redirect(reverse("home"))
    else:
        return redirect(reverse("login"))


@require_POST
def playlist(request):
    """
    API endpoint to schedule generate_playlist tasks
    """
    data = json.loads(request.body.decode("utf-8"))
    schema = {
        "type": "object",
        "required": ["playlist", "platform"],
        "properties": {
            "playlist": {"type": "string"},
            "platform": {"enum": ["spotify", "apple-music"]},
        },
    }
    try:
        validate(data, schema=schema)
    except JsonSchemaValitadionError as e:
        return JsonResponse({"message": e.message}, status=400)
    playlist = data["playlist"]
    platform = data["platform"]
    try:
        if platform == "apple-music":
            validate_spotify_playlist_url(playlist)
            token = request.headers.get("Music-User-Token")
            result = generate_applemusic_playlist.delay(playlist, token)
        elif platform == "spotify":
            validate_apple_music_playlist_url(playlist)
            result = generate_spotify_playlist.delay(playlist)
        else:
            return JsonResponse({"message": "Platform not supported"}, status=400)
    except DjangoValidationError as e:
        return JsonResponse({"message": e.message[0]}, status=400)
    return JsonResponse({"task_id": result.task_id})


@require_POST
def expand(request):
    data = json.loads(request.body.decode("utf-8"))
    url = data.get("url")
    session = requests_retry_session()
    try:
        response = session.head(url, allow_redirects=True, timeout=1)
        response.raise_for_status()
        return JsonResponse({"url": response.url})
    except Exception:
        return JsonResponse({"message": "Link not found."}, status=404)


@require_POST
def add_subscriber(request):
    data = json.loads(request.body.decode("utf-8"))
    email = data.get("email")
    try:
        subscriber = Subscriber.objects.create(email=email)
        return JsonResponse({"email": subscriber.email}, status=201)
    except Exception:
        return JsonResponse({}, status=400)


def ads_txt(request):
    content = "google.com, pub-3322094653674275, DIRECT, f08c47fec0942fa0"
    return HttpResponse(content, content_type="text/plain")


def robots_txt(request):
    content = """User-agent: *
Allow: /

Sitemap: https://playlistor.io/sitemap.xml"""
    return HttpResponse(content, content_type="text/plain")


@login_required(login_url="/login")
def index(request):
    redis_client = get_redis_client()
    count = int((redis_client.get("counter:playlists") or 0))
    playlists = Playlist.objects.filter(
        spotify_url__isnull=False, applemusic_url__isnull=False
    ).order_by("-created_at")[:3]
    response = render(request, "index.html", {"playlists": playlists, "count": count})
    response["Referrer-Policy"] = "origin-when-cross-origin"
    return response
