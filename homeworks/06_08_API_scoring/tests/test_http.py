import json
from http.client import HTTPConnection
from http.server import HTTPServer
from threading import Thread

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

import api


@pytest.fixture
def http_connection(store):
    server = HTTPServer(("127.0.0.1", 0), api.MainHTTPHandler)
    server.store = store
    worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    worker.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        yield connection
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def post(connection, body, path="/method"):
    connection.request(
        "POST",
        path,
        body=body.encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with connection.getresponse() as response:
        return response.status, json.loads(response.read())


@pytest.mark.parametrize(
    "cached_value, expected",
    [(None, 3.0), ("0.0", 0.0)],
    ids=["cache_miss", "cached_zero"],
)
def test_http_online_score(
    http_connection, valid_request, redis_client, cached_value, expected
):
    redis_client.get.return_value = cached_value

    status, body = post(http_connection, json.dumps(valid_request))

    assert status == api.OK
    assert body == {"code": api.OK, "response": {"score": expected}}
    redis_client.get.assert_called_once()


def test_http_clients_interests(http_connection, valid_request, redis_client):
    valid_request["method"] = "clients_interests"
    valid_request["arguments"] = {"client_ids": [1, 2]}
    redis_client.get.side_effect = {"i:1": '["books"]'}.get

    status, body = post(http_connection, json.dumps(valid_request))

    assert status == api.OK
    assert body == {"code": api.OK, "response": {"1": ["books"], "2": []}}


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection_error", "timeout"],
)
def test_http_score_when_store_is_unavailable(
    http_connection, valid_request, redis_client, error_type
):
    redis_client.get.side_effect = error_type("offline")
    redis_client.set.side_effect = error_type("offline")

    status, body = post(http_connection, json.dumps(valid_request))

    assert status == api.OK
    assert body == {"code": api.OK, "response": {"score": 3.0}}
    assert redis_client.get.call_count == 2
    assert redis_client.set.call_count == 2


@pytest.mark.parametrize(
    "error_type",
    [RedisConnectionError, RedisTimeoutError],
    ids=["connection_error", "timeout"],
)
def test_http_interests_when_store_is_unavailable(
    http_connection, valid_request, redis_client, error_type
):
    valid_request["method"] = "clients_interests"
    valid_request["arguments"] = {"client_ids": [1]}
    redis_client.get.side_effect = error_type("offline")

    status, body = post(http_connection, json.dumps(valid_request))

    assert status == api.INTERNAL_ERROR
    assert body == {"code": api.INTERNAL_ERROR, "error": "Internal Server Error"}
    assert redis_client.get.call_count == 2


def test_http_rejects_invalid_json(http_connection, redis_client):
    status, body = post(http_connection, "{invalid")

    assert status == api.BAD_REQUEST
    assert body == {"code": api.BAD_REQUEST, "error": "Bad Request"}
    redis_client.get.assert_not_called()
    redis_client.set.assert_not_called()


def test_http_rejects_unknown_path(http_connection, valid_request, redis_client):
    status, body = post(http_connection, json.dumps(valid_request), path="/unknown")

    assert status == api.NOT_FOUND
    assert body == {"code": api.NOT_FOUND, "error": "Not Found"}
    redis_client.get.assert_not_called()
    redis_client.set.assert_not_called()
