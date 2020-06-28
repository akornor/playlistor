import json
from playlistor.celery import app
from celery import shared_task
from celery.signals import task_success
from celery_progress.backend import ProgressRecorder
from django.core.cache import cache
from spotipy import SpotifyException
from .parsers import AppleMusicParser, SpotifyParser
from .models import Playlist
from .utils import (
    grouper,
    get_redis_client,
    get_spotify_client,
    requests_retry_session,
    generate_auth_token,
    strip_qs,
)


@shared_task(bind=True)
def generate_spotify_playlist(self, url):
    url = strip_qs(url)
    if url in cache:
        return cache.get(url)
    progress_recorder = ProgressRecorder(self)
    sp = get_spotify_client()
    uid = sp.current_user()["id"]
    data = AppleMusicParser(url).extract_data()
    playlist_title = data["playlist_title"]
    tracks = data["tracks"]
    creator = data["playlist_creator"]
    n = len(tracks)
    playlist = sp.user_playlist_create(
        uid,
        playlist_title,
        description=f"Created with playlistor.io from the original playlist by {creator} on Apple Music[{url}].",
    )
    playlist_id = playlist["id"]
    tracks_uris = []
    try:
        for i, track in enumerate(tracks):
            try:
                results = sp.search(
                    f"{track.title} {track.artist} {track.featuring}", limit=1
                )
                track_uri = results["tracks"]["items"][0]["uri"]
                tracks_uris.append(track_uri)
            except (IndexError, KeyError):
                continue
            finally:
                progress_recorder.set_progress(i + 1, n)
        # You can add a maximum of 100 tracks per request.
        if len(tracks_uris) > 100:
            for chunk in grouper(100, tracks_uris):
                sp.user_playlist_add_tracks(uid, playlist_id, chunk)
        else:
            sp.user_playlist_add_tracks(uid, playlist_id, tracks_uris)
    except SpotifyException as e:
        # Delete playlist if error occurs while adding songs
        sp.user_playlist_unfollow(uid, playlist_id)
        raise e
    playlist_url = playlist["external_urls"]["spotify"]
    # Store playlist info
    Playlist.objects.create(
        name=playlist_title, spotify_url=playlist_url, applemusic_url=url
    )
    cache.set(url, playlist_url, timeout=3600)
    return playlist_url


@shared_task(bind=True)
def generate_applemusic_playlist(self, url, token):
    url = strip_qs(url)
    progress_recorder = ProgressRecorder(self)
    data = SpotifyParser(url).extract_data()
    tracks = data["tracks"]
    playlist_title = data["playlist_title"]
    creator = data["playlist_creator"]
    playlist_data = []
    n = len(tracks)
    auth_token = generate_auth_token()
    headers = {"Authorization": f"Bearer {auth_token}", "Music-User-Token": token}
    _session = requests_retry_session()
    for i, track in enumerate(tracks):
        try:
            params = {"term": f"{track.title} {track.artist}", "limit": 1}
            response = _session.get(
                "https://api.music.apple.com/v1/catalog/us/search",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            results = response.json()
            song = results["results"]["songs"]["data"][0]
            playlist_data.append({"id": song["id"], "type": song["type"]})
        except:
            continue
        finally:
            progress_recorder.set_progress(i + 1, n)
    payload = {
        "attributes": {
            "name": playlist_title,
            "description": f"Created with playlistor.io from the original playlist by {creator} on Spotify[{url}].",
        },
        "relationships": {"tracks": {"data": playlist_data}},
    }
    # create playlist here
    response = _session.post(
        "https://api.music.apple.com/v1/me/library/playlists",
        data=json.dumps(payload),
        headers=headers,
    )
    response.raise_for_status()
    return "Check your recently created playlists on Apple Music."


@task_success.connect
def handle_task_success(**kwargs):
    redis_client = get_redis_client()
    redis_client.incr("counter:playlists")
