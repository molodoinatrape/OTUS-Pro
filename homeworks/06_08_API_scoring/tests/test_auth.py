import hashlib

import pytest

import api


@pytest.mark.parametrize(
    "time_text, expected",
    [
        ("2026100812", True),
        ("2026100811", False),
        ("invalid", False),
    ],
    ids=[
        "current_hour",
        "previous_hour",
        "wrong_token_source",
    ],
)
def test_admin_auth(fixed_time, time_text, expected):
    token = hashlib.sha512((time_text + api.ADMIN_SALT).encode("utf-8")).hexdigest()

    request = api.MethodRequest(
        {
            "login": "admin",
            "method": "online_score",
            "token": token,
            "arguments": {},
        }
    )

    assert request.errors == {}
    assert api.check_auth(request) is expected


@pytest.mark.parametrize(
    "account, token_source, expected",
    [
        ("company", "companyuser", True),
        (None, "user", True),
        ("", "user", True),
        ("company", "companyother", False),
        ("company", "othercompanyuser", False),
        (None, "invalid", False),
    ],
    ids=[
        "companyuser",
        "None_user",
        "user",
        "companyother",
        "othercompanyuser",
        "invalid",
    ],
)
def test_user_auth(account, token_source, expected):
    token = hashlib.sha512((token_source + api.SALT).encode("utf-8")).hexdigest()

    request = api.MethodRequest(
        {
            "account": account,
            "login": "user",
            "method": "online_score",
            "token": token,
            "arguments": {},
        }
    )

    assert request.errors == {}
    assert api.check_auth(request) is expected
