import hashlib
from datetime import datetime
from unittest.mock import Mock

import pytest
import redis

import api
from store import Store


@pytest.fixture
def score_data():
    return {
        "phone": 79990000000,
        "email": "text@text.com",
    }


@pytest.fixture
def fixed_time(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 8, 12, 0, tzinfo=tz)

    monkeypatch.setattr("api.datetime.datetime", FixedDatetime)


@pytest.fixture
def redis_client():
    client = Mock(spec=redis.Redis)
    client.get.return_value = None
    client.set.return_value = True
    return client


@pytest.fixture
def store(redis_client):
    return Store(redis_client, retries=1)


@pytest.fixture
def valid_request():
    token = hashlib.sha512(("companyuser" + api.SALT).encode("utf-8")).hexdigest()
    return {
        "account": "company",
        "login": "user",
        "method": "online_score",
        "token": token,
        "arguments": {"phone": "79990000000", "email": "user@example.com"},
    }
