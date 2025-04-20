import datetime
import functools
import re
import subprocess
from urllib.parse import urlsplit

import jwt
import redis
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from spotipy import Spotify

from main import oauth_manager

from .client import AppleMusicClient

SPOTIFY_PLAYLIST_URL_PAT = re.compile(
    r"http(s)?:\/\/open.spotify.com/(user\/.+\/)?playlist/(?P<playlist_id>[^\s?]+)"
)
APPLE_MUSIC_PLAYLIST_URL_PAT = re.compile(
    r"https:\/\/(embed.)?music\.apple\.com\/(?P<storefront>.{2})\/playlist(\/.+)?\/(?P<playlist_id>[^\s?]+)"
)


def requests_retry_session(
    retries=3,
    backoff_factor=1,
    status_forcelist=(429, 500, 502, 503, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_spotify_client():
    return Spotify(oauth_manager=oauth_manager)


def get_applemusic_client():
    return AppleMusicClient(
        settings.APPLE_TEAM_ID, settings.APPLE_KEY_ID, settings.APPLE_PRIVATE_KEY
    )


def grouper(n, iterable):
    return [iterable[i : i + n] for i in range(0, len(iterable), n)]


def get_redis_client():
    return redis.Redis.from_url(settings.REDIS_URL)


def generate_auth_token() -> str:
    # see https://developer.apple.com/documentation/applemusicapi/getting_keys_and_creating_tokens

    return "Al58wnohwlrPfnCK5u2Kq1J++1arL/P2m7zs4fknZjiA5J5Ct95OKNOjbMWYFBHIUed/ttVrX1SymV2TT4nJploDh6H63qkb3COUSA89PIRecX1aqUnnJFOjzkD6AVJvd7puRMPnj4fR9buHduGI9BTFN3zQ4b1Zh9KkOxF8U6heofaEL7QfMdmNz4JNpVAhDxZ7yqBXOYSUS6nUP+oMhPKHELY2jZJqwjDvmsReGtpjxQ09zA=="


def strip_qs(url):
    # Strips query string from url
    return urlsplit(url)._replace(query=None, fragment=None).geturl()


def check_config():
    if not settings.APPLE_KEY_ID:
        raise ImproperlyConfigured(
            "APPLE_KEY_ID setting has not been properly defined."
        )
    if not settings.APPLE_TEAM_ID:
        raise ImproperlyConfigured(
            "APPLE_TEAM_ID setting has not been properly defined."
        )
    if not settings.APPLE_PRIVATE_KEY:
        raise ImproperlyConfigured(
            "APPLE_PRIVATE_KEY setting has not been properly defined."
        )
    if not settings.SPOTIFY_CLIENT_ID:
        raise ImproperlyConfigured(
            "SPOTIFY_CLIENT_ID setting has not been properly defined."
        )
    if not settings.SPOTIFY_CLIENT_SECRET:
        raise ImproperlyConfigured(
            "SPOTIFY_CLIENT_SECRET has not been properly defined."
        )
    if not settings.SPOTIFY_REDIRECT_URI:
        raise ImproperlyConfigured(
            "SPOTIFY_REDIRECT_URI has not been properly defined."
        )
    if not settings.REDIS_URL:
        raise ImproperlyConfigured("REDIS_URL has not been properly defined.")


def sanitize_track_name(name):
    PAT = re.compile(r"\((.+)\)|\[(.+)\]")
    # Remove content in brackets as it tends to be too much noise for track resolution.
    # Free Trial (feat. Qari & Phoelix) [Explicit] -> Free Trial
    # This is a temporary fix until I properly understand the problem space to come up with a more general solution.
    mo = PAT.search(name)
    if mo:
        name = PAT.sub("", name).strip()
    # This is pretty naive. But this is done to remove noisy parts of track name. For example, Loving Cup - (Live At The Beacon Theatre, New York / 2006) -> Loving Cup
    name, *parts = name.partition("-")
    return name


@functools.lru_cache(maxsize=128)
def get_version():
    version = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], universal_newlines=True
    ).strip()
    return version


def validate_playlist_url(pattern, url, platform):
    mo = pattern.match(url)
    if not mo:
        raise ValidationError(f"Invalid {platform} playlist url")
    return url


def validate_apple_music_playlist_url(url):
    validate_playlist_url(APPLE_MUSIC_PLAYLIST_URL_PAT, url, "Apple Music")


def validate_spotify_playlist_url(url):
    validate_playlist_url(SPOTIFY_PLAYLIST_URL_PAT, url, "Spotify")
