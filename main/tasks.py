import json
from playlistor.celery import app
from celery import shared_task
from celery.signals import task_success
from celery_progress.backend import ProgressRecorder
from django.core.cache import cache
from django.conf import settings
from spotipy import SpotifyException
from .parsers import AppleMusicParser, SpotifyParser
from .models import Playlist, Track
from .utils import (
    grouper,
    get_redis_client,
    get_spotify_client,
    get_applemusic_client,
    requests_retry_session,
    generate_auth_token,
    strip_qs,
)

def incr_playlist_count():
    redis_client = get_redis_client()
    redis_client.incr("counter:playlists")

def get_track(**kwargs):
    try:
        return Track.objects.get(**kwargs)
    except Track.DoesNotExist:
        return None

@shared_task(bind=True)
def generate_spotify_playlist(self, url):
    url = strip_qs(url)
    if not settings.DEBUG:
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
    track_uris = []
    tracks_to_save = []
    for i, track in enumerate(tracks):
        try:
            t = get_track(apple_music_id=track.id)
            if t is not None:
                track_uris.append(f"spotify:track:{t.spotify_id}")
            else:
                results = sp.search(
                    f"{track.name} {' '.join(track.artists)}", limit=1
                )
                track_id = results["tracks"]["items"][0]["id"]
                track_uris.append(f"spotify:track:{track_id}")
                tracks_to_save.append(Track(name=track.name, artists=','.join(track.artists), apple_music_id=track.id, spotify_id=track_id))
        except:
            continue
        finally:
            progress_recorder.set_progress(i + 1, n)
    playlist = sp.user_playlist_create(
        uid,
        playlist_title,
        description=f"Created with playlistor.io from the original playlist by {creator} on Apple Music[{url}]."
        if creator
        else f"Created with playlistor.io from the original playlist on Apple Music[{url}].",
    )
    playlist_id = playlist["id"]
    playlist_url = playlist["external_urls"]["spotify"]
    # You can add a maximum of 100 tracks per request.
    if len(track_uris) > 100:
        for chunk in grouper(100, track_uris):
            sp.playlist_add_items(playlist_id, chunk)
    else:
        sp.playlist_add_items(playlist_id, track_uris)
    # Store playlist info
    Playlist.objects.create(
        name=playlist_title, spotify_url=playlist_url, applemusic_url=url
    )
    if len(tracks_to_save) > 0:
        Track.objects.bulk_update_or_create(tracks_to_save, ['name', 'artists', 'apple_music_id', 'spotify_id'], match_field='spotify_id')
    cache.set(url, playlist_url, timeout=3600)
    incr_playlist_count()
    return playlist_url


@shared_task(bind=True)
def generate_applemusic_playlist(self, url, token):
    url = strip_qs(url)
    progress_recorder = ProgressRecorder(self)
    data = SpotifyParser(url).extract_data()
    tracks = data["tracks"]
    playlist_title = data["playlist_title"]
    creator = data["playlist_creator"]
    tracks_to_save = []
    track_ids = []
    n = len(tracks)
    am = get_applemusic_client()
    am.access_token = token
    auth_token = generate_auth_token()
    headers = {"Authorization": f"Bearer {auth_token}", "Music-User-Token": token}
    _session = requests_retry_session()
    for i, track in enumerate(tracks):
        try:
            t = get_track(spotify_id=track.id)
            if t is not None:
                playlist_data.append({"id": t.apple_music_id, "type": "songs"})
                track_ids.append(t.apple_music_id)
            else:
                # use single artist as it's observed to improve search accuracy.
                query = f"{track.name} {track.artists[0]}"
                song = am.search(query=query, limit=1)["results"]["songs"]["data"][0]
                track_ids.append(song["id"])
                tracks_to_save.append(Track(name=track.name, artists=','.join(track.artists), apple_music_id=song["id"], spotify_id=track.id))
        except:
            continue
        finally:
            progress_recorder.set_progress(i + 1, n)
    if len(track_ids) > 200:
        playlist_data =am.user_playlist_create(name=playlist_title, description=f"Created with playlistor.io from the original playlist by {creator} on Spotify[{url}].", track_ids=track_ids[:200])
        playlist_id = playlist_data["data"][0]["id"]
        track_ids = track_ids[200:]
        for chunk in grouper(200, track_ids):
            am.user_playlist_add_tracks(playlist_id, chunk)
    else:
        am.user_playlist_create(name=playlist_title, description=f"Created with playlistor.io from the original playlist by {creator} on Spotify[{url}].", track_ids=track_ids)
    incr_playlist_count()
    if len(tracks_to_save) > 0:
        Track.objects.bulk_update_or_create(tracks_to_save, ['name', 'artists', 'apple_music_id', 'spotify_id'], match_field='apple_music_id')
    return "Check your recently created playlists on Apple Music."