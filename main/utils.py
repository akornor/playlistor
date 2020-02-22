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


def requests_retry_session(
    retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_spotify_client():
    token = oauth.get_cached_token()["access_token"]
    return Spotify(auth=token)


def fetch_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def grouper(n, iterable):
    return [iterable[i : i + n] for i in range(0, len(iterable), n)]

redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL)

def get_redis_client():
    return redis.Redis(connection_pool=redis_pool)

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
    return token.decode()

def strip_qs(url):
    # Strips query string from url
    return urlsplit(url)._replace(query=None).geturl()

def check_config():
    if not settings.APPLE_KEY_ID:
        raise ImproperlyConfigured("APPLE_KEY_ID setting has not been properly defined.")
    if not settings.APPLE_TEAM_ID:
        raise ImproperlyConfigured("APPLE_TEAM_ID setting has not been properly defined.")
    if not settings.APPLE_PRIVATE_KEY:
        raise ImproperlyConfigured("APPLE_PRIVATE_KEY setting has not been properly defined.")
    if not settings.SPOTIFY_CLIENT_ID:
        raise ImproperlyConfigured("SPOTIFY_CLIENT_ID setting has not been properly defined.")
    if not settings.SPOTIFY_CLIENT_SECRET:
        raise ImproperlyConfigured("SPOTIFY_CLIENT_SECRET has not been properly defined.")
    if not settings.REDIRECT_URI:
        raise ImproperlyConfigured("REDIRECT_URI has not been properly defined.")
    if not settings.REDIS_URL:
        raise ImproperlyConfigured("REDIS_URL has not been properly defined.")
