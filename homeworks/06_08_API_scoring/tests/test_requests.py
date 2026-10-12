import pytest

from api import BaseRequest, CharField, OnlineScoreRequest, PhoneField


class DemoRequest(BaseRequest):
    username = CharField(required=True, nullable=False)
    phone = PhoneField(required=False, nullable=True)


class OptionalNameRequest(DemoRequest):
    username = CharField(required=False, nullable=True)


@pytest.mark.parametrize(
    "data,expected_errors,expected_username,expected_phone",
    [
        ({}, {"username"}, None, None),
        ({"username": "alice", "phone": 79990000000}, set(), "alice", "79990000000"),
        ({"username": 123, "phone": 79990000000}, {"username"}, None, "79990000000"),
        ({"username": 123, "phone": "bad"}, {"username", "phone"}, None, None),
        ({"username": "alice", "extra": "ignored"}, set(), "alice", None),
    ],
    ids=["empty", "full", "bad_username", "bad_username_and_phone", "extra_arg"],
)
def test_base_request_validation(
    data, expected_errors, expected_username, expected_phone
):
    request = DemoRequest(data)

    assert set(request.errors) == set(expected_errors)
    assert request.username == expected_username
    assert request.phone == expected_phone
    assert not hasattr(request, "extra")


def test_base_request_validation_uses_overridden_field():
    fields = OptionalNameRequest.get_fields()
    request = OptionalNameRequest({"phone": 79990000000})

    assert set(fields) == {"username", "phone"}
    assert fields["username"] is OptionalNameRequest.username
    assert fields["phone"] is DemoRequest.phone

    assert request.phone == "79990000000"
    assert request.username is None
    assert request.errors == {}


@pytest.mark.parametrize(
    "data,expected_errors",
    [
        ({}, {"arguments"}),
        ({"phone": 79990000000}, {"arguments"}),
        ({"email": "test@test.ru"}, {"arguments"}),
        ({"first_name": "test"}, {"arguments"}),
        ({"birthday": "01.01.2000"}, {"arguments"}),
        ({"phone": 79990000000, "email": "test@test.ru"}, set()),
        ({"first_name": "test", "last_name": "test"}, set()),
        ({"birthday": "01.01.2000", "gender": 0}, set()),
        ({"phone": 79990000000, "email": "test@test.ru", "gender": -1}, {"gender"}),
    ],
    ids=[
        "empty",
        "phone",
        "email",
        "first_name",
        "birthday",
        "phone_and_email",
        "first_name_and_last_name",
        "birthday_and_gender",
        "phone_and_email_and_gender",
    ],
)
def test_online_score_request_validation(data, expected_errors):
    request = OnlineScoreRequest(data)
    assert request.errors.keys() == expected_errors


def test_online_score_request_from_fixture(score_data):
    request = OnlineScoreRequest(score_data)
    assert request.errors == {}
    assert request.phone == "79990000000"


def test_online_score_request_rejects_invalid_gender(score_data):
    score_data["gender"] = -1
    request = OnlineScoreRequest(score_data)
    assert set(request.errors) == {"gender"}
