import requests
from django.conf import settings
import redis


def fetch_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def grouper(n, iterable):
    return [iterable[i : i + n] for i in range(0, len(iterable), n)]


def get_redis_client():
    return redis.Redis.from_url(settings.REDIS_URL)


redis_client = get_redis_client()
