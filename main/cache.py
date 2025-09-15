from functools import wraps

from django.core.cache import cache


def cache_with_key(keyfunc, timeout):
    def decorator(func):
        @wraps(func)
        def func_with_caching(*args, **kwargs):
            key = keyfunc(*args, **kwargs)
            try:
                value = cache.get(key)
            except:
                return func(*args, **kwargs)
            if value is not None:
                return value
            value = func(*args, **kwargs)
            cache.set(key, value, timeout=timeout)
            return value

        return func_with_caching

    return decorator
