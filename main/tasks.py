import json
from audible.celery import app
from celery import shared_task
from celery_progress.backend import ProgressRecorder
from spotipy import SpotifyException
from .parsers import AppleMusicParser, SpotifyParser
from .utils import (
    grouper,
    get_redis_client,
    get_spotify_client,
    requests_retry_session,
    generate_auth_token,
)


@shared_task(bind=True)
def generate_spotify_playlist(self, url):
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
    playlist_url = playlist["external_urls"]["spotify"]
    # Store playlist info
    redis_client = get_redis_client()
    redis_client.lpush(
        "playlists",
        json.dumps(
            {
                "spotify_url": playlist_url,
                "applemusic_url": url,
                "name": playlist_title,
            }
        ),
    )
    return playlist_url


@shared_task(bind=True)
def generate_applemusic_playlist(self, url, token):
    progress_recorder = ProgressRecorder(self)
    data = SpotifyParser(url).extract_data()
    tracks = data["tracks"]
    playlist_title = data["playlist_title"]
    playlist_data = []
    n = len(tracks)
    auth_token = generate_auth_token()
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Music-User-Token": token
    }
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
            "description": f"Originally created on Spotify[{url}]",
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
