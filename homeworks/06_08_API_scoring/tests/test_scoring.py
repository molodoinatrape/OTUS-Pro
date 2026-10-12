import json
from datetime import datetime
from unittest.mock import Mock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from scoring import get_interests, get_score
from store import Store


@pytest.mark.parametrize(
    "arguments, expected",
    [
        ({"phone": None, "email": None}, 0),
        ({"phone": 79141799377, "email": None}, 1.5),
        ({"phone": None, "email": "test@test.ru"}, 1.5),
        (
            {
                "phone": None,
                "email": None,
                "first_name": "test",
                "last_name": "test",
            },
            0.5,
        ),
        (
            {
                "phone": None,
                "email": None,
                "birthday": datetime(2000, 1, 1),
                "gender": 0,
            },
            1.5,
        ),
        (
            {
                "phone": None,
                "email": None,
                "birthday": datetime(2000, 1, 1),
                "gender": None,
            },
            0,
        ),
        (
            {
                "phone": 79141799377,
                "email": "test@test.ru",
                "birthday": datetime(2000, 1, 1),
                "gender": 1,
                "first_name": "test",
                "last_name": "test",
            },
            5.0,
        ),
    ],
    ids=[
        "empty",
        "phone_only",
        "email_only",
        "first_name_and_last_name",
        "birthday_and_gender_0",
        "birthday_and_gender_None",
        "all",
    ],
)
def test_get_score_formula(arguments, expected):
    mock_redis = Mock()
    mock_redis.cache_get.return_value = None

    assert get_score(store=mock_redis, **arguments) == expected


@pytest.mark.parametrize(
    "stored_value, expected",
    [
        ('["music", "books"]', ["music", "books"]),
        (None, []),
    ],
    ids=[
        "found",
        "missing",
    ],
)
def test_get_interests(stored_value, expected):
    mock_redis = Mock()
    mock_redis.get.return_value = stored_value

    result = get_interests(mock_redis, 42)

    mock_redis.get.assert_called_once_with("i:42")
    assert result == expected


def test_get_interests_storage_error():
    mock_redis = Mock()
    mock_redis.get.side_effect = ConnectionError("Storage unavailable")

    with pytest.raises(ConnectionError):
        get_interests(mock_redis, 42)

    mock_redis.get.assert_called_once_with("i:42")


@pytest.mark.parametrize(
    "cached_value, expected",
    [(0.0, 0.0), ("3.0", 3.0)],
    ids=[
        "cached_zero",
        "cached_string",
    ],
)
def test_get_score_uses_cached_value(cached_value, expected):
    mock_redis = Mock()
    mock_redis.cache_get.return_value = cached_value

    result = get_score(store=mock_redis, phone=None, email=None)

    assert result == expected
    assert type(result) is float

    mock_redis.cache_get.assert_called_once()
    mock_redis.cache_set.assert_not_called()


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection error", "timeout error"],
)
def test_get_score_calculates_when_cache_is_unavailable(error_type):
    mock_redis = Mock()
    mock_redis.get.side_effect = error_type("offline")
    mock_redis.set.side_effect = error_type("offline")

    store = Store(mock_redis, retries=1)

    result = get_score(store=store, phone=79141799377, email="test@test.ru")

    assert result == 3.0
    assert type(result) is float
    assert mock_redis.get.call_count == 2
    assert mock_redis.set.call_count == 2


@pytest.mark.parametrize(
    "stored_value, expected",
    [('["music", "books"]', ["music", "books"]), (None, [])],
    ids=["found", "missing"],
)
def test_get_interests_with_store(stored_value, expected):
    mock_redis = Mock()
    mock_redis.get.return_value = stored_value
    store = Store(mock_redis, retries=1)

    assert get_interests(store, 42) == expected
    mock_redis.get.assert_called_once_with("i:42")
    mock_redis.set.assert_not_called()


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection_error", "timeout"],
)
def test_get_interests_with_store_propagates_storage_error(error_type):
    mock_redis = Mock()
    mock_redis.get.side_effect = error_type("offline")
    store = Store(mock_redis, retries=1)

    with pytest.raises(error_type):
        get_interests(store, 42)

    assert mock_redis.get.call_count == 2
    mock_redis.get.assert_called_with("i:42")
    mock_redis.set.assert_not_called()


def test_get_score_caches_calculated_value():
    store = Mock(spec=Store)
    store.cache_get.return_value = None

    result = get_score(
        store=store,
        phone="79990000000",
        email="user@example.com",
        birthday=datetime(2000, 1, 1),
        gender=0,
        first_name="Ivan",
        last_name="Petrov",
    )

    assert result == 5.0
    store.cache_get.assert_called_once()
    key = store.cache_get.call_args.args[0]
    assert key.startswith("uid:")
    assert json.loads(key.removeprefix("uid:")) == [
        "79990000000",
        "user@example.com",
        "20000101",
        0,
        "Ivan",
        "Petrov",
    ]
    store.cache_set.assert_called_once_with(key, 5.0, 3600)


@pytest.mark.parametrize(
    "changed_argument, changed_value",
    [
        ("phone", "79990000001"),
        ("email", "other@example.com"),
        ("birthday", datetime(2000, 1, 2)),
        ("gender", 1),
        ("first_name", "Petr"),
        ("last_name", "Ivanov"),
    ],
    ids=["phone", "email", "birthday", "gender", "first_name", "last_name"],
)
def test_get_score_key_changes_with_arguments(changed_argument, changed_value):
    store = Mock(spec=Store)
    store.cache_get.return_value = None
    arguments = {
        "phone": "79990000000",
        "email": "user@example.com",
        "birthday": datetime(2000, 1, 1),
        "gender": 0,
        "first_name": "Ivan",
        "last_name": "Petrov",
    }

    get_score(store=store, **arguments)
    first_key = store.cache_get.call_args.args[0]
    arguments[changed_argument] = changed_value
    get_score(store=store, **arguments)
    second_key = store.cache_get.call_args.args[0]

    assert first_key != second_key


@pytest.mark.parametrize("failing_method", ["get", "set"], ids=["read", "write"])
@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection_error", "timeout"],
)
def test_get_score_handles_partial_cache_failure(
    redis_client, store, failing_method, error_type
):
    getattr(redis_client, failing_method).side_effect = error_type("offline")

    assert get_score(store, "79990000000", "user@example.com") == 3.0
    assert redis_client.get.call_count == (2 if failing_method == "get" else 1)
    assert redis_client.set.call_count == (2 if failing_method == "set" else 1)
