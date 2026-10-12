"""Доступ к Redis для кеша оценок и интересов клиентов."""

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry


class Store:
    """Обёртка клиента Redis с повторами сетевых операций."""

    def __init__(self, client, retries=2):
        self.client = client
        self.retries = retries

    def get(self, key):
        return self._call_with_retries(self.client.get, key)

    def cache_get(self, key):
        try:
            return self.get(key)
        except redis.exceptions.ConnectionError, redis.exceptions.TimeoutError:
            return None

    def cache_set(self, key, value, ttl):
        try:
            return self._call_with_retries(self.client.set, key, value, ex=ttl)
        except redis.exceptions.ConnectionError, redis.exceptions.TimeoutError:
            return None

    def _call_with_retries(self, operation, *args, **kwargs):
        """Повторяет вызов при ошибке соединения или таймауте Redis."""
        for attempt in range(self.retries + 1):
            try:
                return operation(*args, **kwargs)
            except redis.exceptions.ConnectionError, redis.exceptions.TimeoutError:
                if attempt == self.retries:
                    raise
        return None


if __name__ == "__main__":
    redis_client = redis.StrictRedis(
        host="127.0.0.1",
        port=6379,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        retry=Retry(NoBackoff(), 0),
    )

    print(redis_client.ping())

    store = Store(redis_client)
    store.cache_set("practice:score", 3.0, 60)
    cache = store.cache_get("practice:score")
    print(cache, type(cache))
