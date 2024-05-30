import json
import requests
from playlistor.celery import app
from celery import shared_task
from celery.utils.log import get_task_logger
from celery_progress.backend import ProgressRecorder
from django.core.cache import cache
from django.conf import settings
from django.db import IntegrityError
from spotipy import SpotifyException
from .parsers import get_apple_music_playlist_data, get_spotify_playlist_data, SPOTIFY_PLAYLIST_URL_PAT, APPLE_MUSIC_PLAYLIST_URL_PAT
from .models import Playlist, Track
from .utils import (
    grouper,
    get_redis_client,
    get_spotify_client,
    get_applemusic_client,
    strip_qs,
)
from .counters import Counters

logger = get_task_logger(__name__)

counters = Counters()


@shared_task(bind=True)
def generate_spotify_playlist(self, url):
    def save_or_update_tracks(tracks):
        try:
            Track.objects.bulk_update_or_create(
                tracks,
                ["name", "artists", "apple_music_id", "spotify_id"],
                match_field="spotify_id",
            )
        except IntegrityError as e:
            return

    url = strip_qs(url)
    logger.info(f"Generating spotify equivalent of apple music playlist:{url}")
    progress_recorder = ProgressRecorder(self)
    sp = get_spotify_client()
    uid = sp.current_user()["id"]
    playlist_id = APPLE_MUSIC_PLAYLIST_URL_PAT.match(url).group('playlist_id')
    data = get_apple_music_playlist_data(playlist_id)
    playlist_name = data["playlist_name"]
    tracks = data["tracks"]
    creator = data["curator"]
    artwork_url = data["playlist_artwork_url"]
    n = len(tracks)
    track_uris = []
    tracks_to_save = []
    missed_tracks = []
    for i, track in enumerate(tracks):
        try:
            # Reduce number of artists in query to improve search accuracy
            query = f"{track.name} {' '.join(track.artists if len(track.artists) <= 2 else track.artists[:2])}"
            results = sp.search(query, limit=1)
            track_id = results["tracks"]["items"][0]["id"]
            track_uris.append(f"spotify:track:{track_id}")
            tracks_to_save.append(
                Track(
                    name=track.name,
                    artists=",".join(track.artists),
                    apple_music_id=track.id,
                    spotify_id=track_id,
                )
            )
        except:
            missed_tracks.append(track)
            continue
        finally:
            progress_recorder.set_progress(i + 1, n)
    playlist = sp.user_playlist_create(
        uid,
        playlist_name,
        description=f"Made with Playlistor (https://playlistor.io) :)",
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
        name=playlist_name,
        artwork_url=artwork_url,
        spotify_url=playlist_url,
        applemusic_url=url,
        creator=creator,
    )
    if len(tracks_to_save) > 0:
        save_or_update_tracks(tracks_to_save)
    cache.set(url, playlist_url, timeout=3600)
    counters.incr_playlist_counter()
    logger.info(f"Missed {len(missed_tracks)} in {n} track(s): {missed_tracks}")
    return {
        "playlist_url": playlist_url,
        "number_of_tracks": n,
        "missed_tracks": missed_tracks,
        "source": "apple-music",
        "destination": "spotify",
    }


@shared_task(bind=True)
def generate_applemusic_playlist(self, url, token):
    def save_or_update_tracks(tracks):
        try:
            Track.objects.bulk_update_or_create(
                tracks,
                ["name", "artists", "apple_music_id", "spotify_id"],
                match_field="apple_music_id",
            )
        except IntegrityError as e:
            return

    url = strip_qs(url)
    logger.info(f"Generating apple music equivalent of spotify playlist:{url}")
    progress_recorder = ProgressRecorder(self)
    playlist_id = SPOTIFY_PLAYLIST_URL_PAT.match(url).group('playlist_id')
    data = get_spotify_playlist_data(playlist_id)
    tracks = data["tracks"]
    # For some reason Spotify playlists can have an empty string as playlist name.
    playlist_name = data["playlist_name"] or "Untitled"
    creator = data["curator"]
    tracks_to_save = []
    track_ids = []
    missed_tracks = []
    n = len(tracks)
    am = get_applemusic_client()
    am.access_token = token
    for i, track in enumerate(tracks):
        try:
            # use single artist as it's observed to improve search accuracy.
            query = f"{track.name} {track.artists[0]}"
            song = am.search(query=query, limit=1)["results"]["songs"]["data"][0]
            track_ids.append(song["id"])
            tracks_to_save.append(
                Track(
                    name=track.name,
                    artists=",".join(track.artists),
                    apple_music_id=song["id"],
                    spotify_id=track.id,
                )
            )
        except:
            missed_tracks.append(track)
            continue
        finally:
            progress_recorder.set_progress(i + 1, n)
    try:
        N = 100
        if len(track_ids) > N:
            playlist_data = am.user_playlist_create(
                name=playlist_name,
                description=f"Made with Playlistor (https://playlistor.io) :)",
                track_ids=track_ids[:N],
            )
            playlist_id = playlist_data["data"][0]["id"]
            track_ids = track_ids[N:]
            for chunk in grouper(N, track_ids):
                am.user_playlist_add_tracks(playlist_id, chunk)
        else:
            am.user_playlist_create(
                name=playlist_name,
                description=f"Made with Playlistor (https://playlistor.io) :)",
                track_ids=track_ids,
            )

    except requests.exceptions.HTTPError as e:
        response = e.response
        if response.status_code >= 500:
            if len(tracks_to_save) > 0:
                save_or_update_tracks(tracks_to_save)
            raise self.retry(exc=e, countdown=30)
        else:
            raise e
    counters.incr_playlist_counter()
    if len(tracks_to_save) > 0:
        save_or_update_tracks(tracks_to_save)
    logger.info(f"Missed {len(missed_tracks)} in {n} track(s): {missed_tracks}")
    return {
        "playlist_url": None,
        "number_of_tracks": n,
        "missed_tracks": missed_tracks,
        "source": "spotify",
        "destination": "apple-music",
    }
