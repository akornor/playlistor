import re
import datetime
from urllib.parse import urlsplit
import jwt
import requests
import redis
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from spotipy import Spotify
from main import oauth
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from .client import AppleMusicClient


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
        method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def get_spotify_client():
    token = oauth.get_cached_token()["access_token"]
    return Spotify(auth=token)


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
    time_now = datetime.datetime.now()
    time_expired = time_now + datetime.timedelta(hours=12)
    headers = {"alg": "ES256", "kid": settings.APPLE_KEY_ID}
    payload = {
        "iss": settings.APPLE_TEAM_ID,
        "exp": int(time_expired.strftime("%s")),
        "iat": int(time_now.strftime("%s")),
    }
    token = jwt.encode(
        payload, settings.APPLE_PRIVATE_KEY, algorithm="ES256", headers=headers
    )
    return token


def strip_qs(url):
    # Strips query string from url
    return urlsplit(url)._replace(query=None).geturl()


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


PAT = re.compile(r"\((.+)\)|\[(.+)\]")


def sanitize_track_name(name):
    # Remove content in brackets as it tends to be too much noise for track resolution.
    # Free Trial (feat. Qari & Phoelix) [Explicit] -> Free Trial
    # This is a temporary fix until I properly understand the problem space to come up with a more general solution.
    mo = PAT.search(name)
    if mo:
        name = PAT.sub("", name).strip()
    # This is pretty naive. But this is done to remove noisy parts of track name. For example, Loving Cup - (Live At The Beacon Theatre, New York / 2006) -> Loving Cup
    name, *parts = name.partition("-")
    return name
