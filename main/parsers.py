import re
from collections import namedtuple
from dataclasses import dataclass
from functools import wraps
from typing import List
from urllib.parse import urljoin

from django.core.cache import cache

from .utils import (
    generate_auth_token,
    get_applemusic_client,
    get_spotify_client,
    requests_retry_session,
    sanitize_track_name,
)


@dataclass(frozen=True)
class Track:
    id: str
    name: str
    sanitized_name: str
    artists: List[str]
    duration_ms: int
    isrc: str
    release_date: str


SPOTIFY_PLAYLIST_URL_PAT = re.compile(
    r"http(s)?:\/\/open.spotify.com/(user\/.+\/)?playlist/(?P<playlist_id>[^\s?]+)"
)
APPLE_MUSIC_PLAYLIST_URL_PAT = re.compile(
    r"https:\/\/(embed.)?music\.apple\.com\/(?P<storefront>.{2})\/playlist(\/.+)?\/(?P<playlist_id>[^\s?]+)"
)


def cache_with_key(keyfunc, timeout):
    def decorator(func):
        @wraps(func)
        def func_with_caching(*args, **kwargs):
            key = keyfunc(*args, **kwargs)
            try:
                value = cache.get(key)
            except:
                return func(*args, **kwargs)
            value = func(*args, **kwargs)
            cache.set(key, value, timeout=timeout)
            return value

        return func_with_caching

    return decorator


def spotify_playlist_cache_key(playlist_id):
    return f"playlists:spotify:{playlist_id}"


def apple_music_playlist_cache_key(playlist_id):
    return f"playlists:apple_music:{playlist_id}"


@cache_with_key(spotify_playlist_cache_key, timeout=600)
def get_spotify_playlist_data(playlist_id):
    sp = get_spotify_client()
    playlist = sp.playlist(playlist_id=playlist_id)
    playlist_name = playlist["name"]
    curator = playlist["owner"]["display_name"]
    description = playlist["description"]
    snapshot_id = playlist["snapshot_id"]
    url = playlist["external_urls"]["spotify"]
    playlist_tracks = []
    items = []
    items.extend(playlist["tracks"]["items"])
    track_results = playlist["tracks"]
    has_next = track_results.get("next")
    while has_next is not None:
        track_results = sp.next(track_results)
        items.extend(track_results["items"])
        has_next = track_results.get("next")
    for item in items:
        track = item["track"]
        if track is not None:
            name = track["name"]
            sanitized_name = sanitize_track_name(name)
            duration_ms = track["duration_ms"]
            isrc = track["external_ids"]["isrc"]
            artists = [artist["name"] for artist in track["artists"]]
            release_date = track["album"]["release_date"]
            playlist_tracks.append(
                Track(
                    id=track["id"],
                    name=name,
                    sanitized_name=sanitized_name,
                    artists=artists,
                    duration_ms=duration_ms,
                    isrc=isrc,
                    release_date=release_date,
                )
            )
    return {
        "playlist_name": playlist_name,
        "curator": curator,
        "tracks": playlist_tracks,
        "description": description,
        "snapshot_id": snapshot_id,
        "url": url,
    }


@cache_with_key(apple_music_playlist_cache_key, timeout=600)
def get_apple_music_playlist_data(playlist_id):
    def _get_playlist_artwork_url(data):
        artwork_url = data.get("artwork", {}).get("url")
        if not artwork_url:
            return None
        w, h = data["artwork"]["width"], data["artwork"]["height"]
        artwork_url = artwork_url.replace("{w}", str(w))
        artwork_url = artwork_url.replace("{h}", str(h))
        return artwork_url

    session = requests_retry_session()
    auth_token = generate_auth_token()
    headers = {"Authorization": f"Bearer {auth_token}"}
    API_BASE_URL = "https://api.music.apple.com"
    storefront = "us"
    response = session.get(
        f"{API_BASE_URL}/v1/catalog/{storefront}/playlists/{playlist_id}",
        headers=headers,
    )
    response.raise_for_status()
    playlist_data = response.json()["data"][0]
    playlist_attrs = playlist["attributes"]
    playlist_name = playlist_attrs["name"]
    playlist_curator = playlist_attrs.get("curatorName")
    playlist_artwork_url = _get_playlist_artwork_url(playlist_attrs)
    url = playlist_attrs["url"]
    description = playlist_attrs.get("description", {}).get("short")
    tracks = []
    track_items = []
    track_items.extend(playlist_data["relationships"]["tracks"]["data"])
    next_url = playlist_data["relationships"]["tracks"].get("next")
    while next_url is not None:
        response = session.get(urljoin(API_BASE_URL, next_url), headers=headers)
        data = response.json()
        track_items.extend(data["data"])
        next_url = data.get("next")
    for track in track_items:
        track_attrs = track["attributes"]
        artists = []
        artists.extend(
            track_attrs["artistName"]
            .replace("featuring", ",")  # Lil' Scrappy featuring Young Buck
            .replace("&", ",")  # Rah Digga & Missy Elliot
            .replace(" x ", ",")  # Chloe x Halle
            .split(",")
        )
        name = track_attrs.get("name")
        sanitized_name = sanitize_track_name(name)
        isrc = track_attrs.get("isrc")
        duration_ms = track_attrs.get("durationInMillis")
        release_date = track_attrs.get("releaseDate")
        tracks.append(
            Track(
                id=track["id"],
                name=name,
                artists=artists,
                sanitized_name=sanitized_name,
                duration_ms=duration_ms,
                isrc=isrc,
                release_date=release_date,
            )
        )
    return {
        "playlist_name": playlist_name,
        "curator": playlist_curator,
        "tracks": tracks,
        "description": description,
        "playlist_artwork_url": playlist_artwork_url,
        "url": url,
    }
