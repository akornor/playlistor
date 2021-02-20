from django.utils.functional import cached_property
from redis.exceptions import ConnectionError, ResponseError
from .utils import get_redis_client


PLAYLIST_COUNTER_KEY = "counter:playlists"


class Counters:
    @cached_property
    def _redis(self):
        return get_redis_client()

    def incr(self, key):
        self._redis.incr(key)

    def incr_playlist_counter(self, key=PLAYLIST_COUNTER_KEY):
        self.incr(key)
