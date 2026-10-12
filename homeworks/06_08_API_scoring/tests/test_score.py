from unittest.mock import Mock, call

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from store import Store


@pytest.mark.parametrize(
    "stored_value, key",
    [
        ("3.0", "test:store"),
        (None, "test:store"),
    ],
    ids=[
        "str",
        "None",
    ],
)
def test_get_returns_value(stored_value, key):
    mock_redis = Mock()
    mock_redis.get.return_value = stored_value

    store = Store(mock_redis)

    assert store.get(key) == stored_value
    mock_redis.get.assert_called_once_with(key)


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection_error", "timeout"],
)
def test_get_recovers_after_error(error_type):
    mock_redis = Mock()
    mock_redis.get.side_effect = [
        error_type("offline"),
        "3.0",
    ]

    store = Store(mock_redis)

    assert store.get("test:store") == "3.0"
    assert mock_redis.get.call_count == 2
    assert mock_redis.get.call_args_list == [call("test:store")] * 2


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection error", "timeout error"],
)
@pytest.mark.parametrize(
    "retries", [0, 1, 2], ids=["no_retries", "one_retry", "two_retries"]
)
def test_get_propagates_error_after_retries(error_type, retries):
    mock_redis = Mock()
    mock_redis.get.side_effect = error_type("offline")

    store = Store(mock_redis, retries=retries)

    with pytest.raises(error_type):
        store.get("test:store")
    assert mock_redis.get.call_count == retries + 1
    assert mock_redis.get.call_args_list == [call("test:store")] * (retries + 1)


@pytest.mark.parametrize("stored_value", ["3.0", None], ids=["found", "missing"])
def test_cache_get_returns_value(stored_value):
    mock_redis = Mock()
    mock_redis.get.return_value = stored_value
    store = Store(mock_redis)

    assert store.cache_get("test:store") == stored_value
    mock_redis.get.assert_called_once_with("test:store")


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection error", "timeout error"],
)
@pytest.mark.parametrize(
    "retries", [0, 1, 2], ids=["no_retries", "one_retry", "two_retries"]
)
def test_cache_get_returns_none_after_retries(error_type, retries):
    mock_redis = Mock()
    mock_redis.get.side_effect = error_type("offline")

    store = Store(mock_redis, retries=retries)

    assert store.cache_get("test:store") is None
    assert mock_redis.get.call_count == retries + 1
    assert mock_redis.get.call_args_list == [call("test:store")] * (retries + 1)


def test_cache_set_passes_ttl():
    mock_redis = Mock()
    mock_redis.set.return_value = True

    store = Store(mock_redis)

    assert store.cache_set("test:store", 3.0, 60) is True
    mock_redis.set.assert_called_once_with("test:store", 3.0, ex=60)


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection error", "timeout error"],
)
def test_cache_set_recovers_after_error(error_type):
    mock_redis = Mock()
    mock_redis.set.side_effect = [error_type("offline"), True]

    store = Store(mock_redis, retries=2)

    assert store.cache_set("test:store", 3.0, 60) is True
    assert mock_redis.set.call_count == 2

    assert mock_redis.set.call_args_list == [call("test:store", 3.0, ex=60)] * 2


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection_error", "timeout"],
)
@pytest.mark.parametrize(
    "retries", [0, 1, 2], ids=["no_retries", "one_retry", "two_retries"]
)
def test_cache_set_suppresses_error_after_retries(error_type, retries):
    mock_redis = Mock()
    mock_redis.set.side_effect = error_type("offline")
    store = Store(mock_redis, retries=retries)

    assert store.cache_set("test:store", 3.0, 60) is None
    assert mock_redis.set.call_count == retries + 1
    expected_calls = [call("test:store", 3.0, ex=60)] * (retries + 1)
    assert mock_redis.set.call_args_list == expected_calls


@pytest.mark.parametrize("method", ["get", "cache_get", "cache_set"])
def test_store_does_not_hide_unexpected_errors(method):
    client = Mock()
    operation = client.set if method == "cache_set" else client.get
    operation.side_effect = ValueError("invalid command")
    store = Store(client)
    arguments = ("test:store", 3.0, 60) if method == "cache_set" else ("test:store",)

    with pytest.raises(ValueError, match="invalid command"):
        getattr(store, method)(*arguments)

    operation.assert_called_once()
