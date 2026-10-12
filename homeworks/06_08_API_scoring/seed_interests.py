"""Загружает примеры интересов клиентов в Redis."""

import json

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

INTERESTS = {
    1: ["books", "music"],
    2: ["sport", "travel"],
}


def main():
    """Записывает JSON интересов по ключам i:<client_id>."""
    with redis.Redis(
        host="127.0.0.1",
        port=6379,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        retry=Retry(NoBackoff(), 0),
    ) as client:
        for client_id, interests in INTERESTS.items():
            key = f"i:{client_id}"
            client.set(key, json.dumps(interests))
            print(f"{key}: {interests}")


if __name__ == "__main__":
    main()
