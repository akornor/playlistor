from audible.celery import app
from celery import shared_task
from spotipy import SpotifyException
from .parsers import AppleMusicParser, SpotifyParser
from .utils import (
    fetch_url,
    grouper,
    redis_client,
    get_spotify_client,
    get_access_token,
    requests_retry_session,
)
from celery_progress.backend import ProgressRecorder
import json


@shared_task(bind=True)
def generate_spotify_playlist(self, playlist_url):
    progress_recorder = ProgressRecorder(self)
    token = get_access_token()
    sp = get_spotify_client(token)
    uid = sp.current_user()["id"]
    html = fetch_url(url)
    data = AppleMusicParser(html).extract_data()
    playlist_title = data["playlist_title"]
    tracks = data["tracks"]
    creator = data["playlist_creator"]
    n = len(tracks)
    playlist = sp.user_playlist_create(
        uid,
        playlist_title,
        description=f"Originally created by {creator} on Apple Music[{url}].",
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
    redis_client.lpush(
        "playlists",
        json.dumps(
            {
                "spotify_url": playlist["external_urls"]["spotify"],
                "applemusic_url": url,
                "name": playlist_title,
            }
        ),
    )
    return playlist["external_urls"]["spotify"]


@shared_task(bind=True)
def generate_applemusic_playlist(self, playlist_url):
    progress_recorder = ProgressRecorder(self)
    data = SpotifyParser(playlist_url).extract_data()
    tracks = data["tracks"]
    playlist_title = data["playlist_title"]
    playlist_data = []
    n = len(tracks)
    headers = {
        "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IlEzNzlBOUtBUVYifQ.eyJpc3MiOiIyM05CNDlSRDM0IiwiZXhwIjoxNTcwMzMwNjQzLCJpYXQiOjE1NzAyODc0NDN9.dJ8-L74qFJEgQPRLA2T7RvvDO1LERdYuZhlgH6Tjduio5ZvniR5q-B1tMnOWMcp79tTVHcPbNx7VRrdjIWfBmQ",
        "Music-User-Token": "AptLfToaSMg2Nfcal+VFwxnTQ3CQkcerw66NSQhGzfiMJTPmINrgkysUTns6HQn044cGExqJfF1iBeW9s8PGhWh8jVXuOKIGl/VeLg1QCzB+iYRioD4ZhHtf4baRk2MmBXBgrrwFxBS88/9OGDuiqetZ99LG1lBB5tW+TKiwGXoFeAU808ya/FBFypjHmooAWoGN/xVsGDqMRHy9ob2KdM1Dn80Ia7aunS4EYiIi5e8wfvFkxg==",
    }
    _session = requests_retry_session()
    for i, track in enumerate(tracks):
        params = {"term": f"{track.title} {track.artist}", "limit": 1}
        response = _session.get(
            "https://api.music.apple.com/v1/catalog/us/search",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        results = response.json()
        try:
            song = results["results"]["songs"]["data"][0]
            playlist_data.append({"id": song["id"], "type": song["type"]})
        except KeyError:
            continue
        finally:
            progress_recorder.set_progress(i + 1, n)
    payload = {
        "attributes": {
            "name": playlist_title,
            "description": f"Originally created on Spotify[{playlist_url}]",
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
    return f"Check your recently created playlists on Apple Music."
