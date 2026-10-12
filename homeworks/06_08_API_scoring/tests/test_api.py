import hashlib
from unittest.mock import call

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

import api


@pytest.mark.parametrize(
    "cached_value, expected",
    [(None, 3.0), ("0.0", 0.0), ("4.5", 4.5)],
    ids=["cache_miss", "cached_zero", "cache_hit"],
)
def test_online_score(valid_request, store, redis_client, cached_value, expected):
    redis_client.get.return_value = cached_value
    context = {}

    response, code = api.method_handler({"body": valid_request}, context, store)

    assert code == api.OK
    assert response == {"score": expected}
    assert set(context["has"]) == {"phone", "email"}
    redis_client.get.assert_called_once()
    if cached_value is None:
        key = redis_client.get.call_args.args[0]
        redis_client.set.assert_called_once_with(key, 3.0, ex=3600)
    else:
        redis_client.set.assert_not_called()


def test_admin_score_does_not_use_store(valid_request, store, redis_client, fixed_time):
    valid_request["login"] = "admin"
    token_source = api.datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT
    valid_request["token"] = hashlib.sha512(token_source.encode("utf-8")).hexdigest()

    response, code = api.method_handler({"body": valid_request}, {}, store)

    assert code == api.OK
    assert response == {"score": 42}
    redis_client.get.assert_not_called()
    redis_client.set.assert_not_called()


def test_clients_interests(valid_request, store, redis_client):
    valid_request["method"] = "clients_interests"
    valid_request["arguments"] = {"client_ids": [1, 2]}
    values = {"i:1": '["books", "music"]'}
    redis_client.get.side_effect = values.get
    context = {}

    response, code = api.method_handler({"body": valid_request}, context, store)

    assert code == api.OK
    assert response == {1: ["books", "music"], 2: []}
    assert context["nclients"] == 2
    assert redis_client.get.call_args_list == [call("i:1"), call("i:2")]
    redis_client.set.assert_not_called()


def test_clients_interests_with_duplicate_ids(valid_request, store, redis_client):
    valid_request["method"] = "clients_interests"
    valid_request["arguments"] = {"client_ids": [1, 1, 2]}
    redis_client.get.return_value = '["books"]'
    context = {}

    response, code = api.method_handler({"body": valid_request}, context, store)

    assert code == api.OK
    assert response == {1: ["books"], 2: ["books"]}
    assert context["nclients"] == 3


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection_error", "timeout"],
)
def test_online_score_when_store_is_unavailable(
    valid_request, store, redis_client, error_type
):
    redis_client.get.side_effect = error_type("offline")
    redis_client.set.side_effect = error_type("offline")

    response, code = api.method_handler({"body": valid_request}, {}, store)

    assert code == api.OK
    assert response == {"score": 3.0}
    assert redis_client.get.call_count == 2
    assert redis_client.set.call_count == 2


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection_error", "timeout"],
)
def test_clients_interests_propagates_store_error(
    valid_request, store, redis_client, error_type
):
    valid_request["method"] = "clients_interests"
    valid_request["arguments"] = {"client_ids": [1]}
    redis_client.get.side_effect = error_type("offline")

    with pytest.raises(error_type):
        api.method_handler({"body": valid_request}, {}, store)

    assert redis_client.get.call_args_list == [call("i:1")] * 2


@pytest.mark.parametrize("body", [None, [], "text"], ids=["none", "list", "string"])
def test_method_handler_rejects_invalid_body(body, store, redis_client):
    response, code = api.method_handler({"body": body}, {}, store)

    assert code == api.INVALID_REQUEST
    assert response == "Body must be dict"
    redis_client.get.assert_not_called()
    redis_client.set.assert_not_called()


def test_invalid_score_request_does_not_use_store(valid_request, store, redis_client):
    valid_request["arguments"]["phone"] = "bad"

    response, code = api.method_handler({"body": valid_request}, {}, store)

    assert code == api.INVALID_REQUEST
    assert "phone" in response
    redis_client.get.assert_not_called()
    redis_client.set.assert_not_called()


def test_bad_auth_does_not_use_store(valid_request, store, redis_client):
    valid_request["token"] = "bad"

    response, code = api.method_handler({"body": valid_request}, {}, store)

    assert code == api.FORBIDDEN
    assert response == "Forbidden"
    redis_client.get.assert_not_called()
    redis_client.set.assert_not_called()


@pytest.mark.parametrize(
    "method", ["unknown", "", None], ids=["unknown", "empty", "none"]
)
def test_unknown_method_does_not_use_store(valid_request, store, redis_client, method):
    valid_request["method"] = method

    response, code = api.method_handler({"body": valid_request}, {}, store)

    assert code == api.NOT_FOUND
    assert response == "Unknown method"
    redis_client.get.assert_not_called()
    redis_client.set.assert_not_called()
