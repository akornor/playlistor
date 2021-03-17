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
from .parsers import AppleMusicParser, SpotifyParser
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


def get_track(**kwargs):
    try:
        return Track.objects.get(**kwargs)
    except Track.DoesNotExist:
        return None


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
    logger.info(f"Generating spotify playlist for apple music playlist:{url}")
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
    missed_tracks = []
    for i, track in enumerate(tracks):
        try:
            t = get_track(apple_music_id=track.id)
            if t is not None:
                track_uris.append(f"spotify:track:{t.spotify_id}")
            else:
                results = sp.search(f"{track.name} {' '.join(track.artists)}", limit=1)
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
        uid, playlist_title, description=f"Made with https://playlistor.io :)"
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
        save_or_update_tracks(tracks_to_save)
    cache.set(url, playlist_url, timeout=3600)
    counters.incr_playlist_counter()
    logger.info(f"Missed {len(missed_tracks)} in {n} track(s): {missed_tracks}")
    return playlist_url


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
    logger.info(f"Generating apple music playlist for spotify playlist:{url}")
    progress_recorder = ProgressRecorder(self)
    data = SpotifyParser(url).extract_data()
    tracks = data["tracks"]
    # For some reason Spotify playlists can have an empty string as playlist name.
    playlist_title = data["playlist_title"] or "Untitled"
    creator = data["playlist_creator"]
    tracks_to_save = []
    track_ids = []
    missed_tracks = []
    n = len(tracks)
    am = get_applemusic_client()
    am.access_token = token
    for i, track in enumerate(tracks):
        try:
            t = get_track(spotify_id=track.id)
            if t is not None:
                track_ids.append(t.apple_music_id)
            else:
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
                name=playlist_title,
                description=f"Made with https://playlistor.io :)",
                track_ids=track_ids[:N],
            )
            playlist_id = playlist_data["data"][0]["id"]
            track_ids = track_ids[N:]
            for chunk in grouper(N, track_ids):
                am.user_playlist_add_tracks(playlist_id, chunk)
        else:
            am.user_playlist_create(
                name=playlist_title,
                description=f"Made with https://playlistor.io :)",
                track_ids=track_ids,
            )

    except requests.exceptions.HTTPError as e:
        response = e.response
        if response.status_code in [500]:
            if len(tracks_to_save) > 0:
                save_or_update_tracks(tracks_to_save)
            raise self.retry(exc=e, countdown=30)
        else:
            raise e
    counters.incr_playlist_counter()
    if len(tracks_to_save) > 0:
        save_or_update_tracks(tracks_to_save)
    logger.info(f"Missed {len(missed_tracks)} in {n} track(s): {missed_tracks}")
    return "Check your recently created playlists on Apple Music."
