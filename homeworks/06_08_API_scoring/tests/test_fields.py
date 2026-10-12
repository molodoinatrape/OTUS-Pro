from datetime import date

import pytest

from api import (
    ArgumentsField,
    BirthDayField,
    CharField,
    ClientIDsField,
    DateField,
    EmailField,
    GenderField,
    PhoneField,
)


# Проверка CharField
@pytest.mark.parametrize(
    "nullable, value, expected",
    [
        (False, "hello", "hello"),
        (True, None, None),
        (True, "", ""),
    ],
    ids=[
        "hello",
        "None",
        "empty",
    ],
)
def test_char_field_validate(nullable, value, expected):
    field = CharField(nullable=nullable)
    assert field.validate(value) == expected


@pytest.mark.parametrize(
    "nullable, value",
    [
        (False, None),
        (False, ""),
        (False, 123),
        (True, 123),
    ],
    ids=[
        "None",
        "empty",
        "int_not_nullable",
        "int_nullable",
    ],
)
def test_char_field_reject_invalid(nullable, value):
    field = CharField(nullable=nullable)
    with pytest.raises(ValueError):
        field.validate(value)


# Проверка ArgumentsField
@pytest.mark.parametrize(
    "nullable, value, expected",
    [
        (False, {"key": "value"}, {"key": "value"}),
        (True, {}, {}),
        (True, None, None),
    ],
    ids=[
        "not_nullable",
        "empty",
        "None",
    ],
)
def test_arguments_field_validate(nullable, value, expected):
    field = ArgumentsField(nullable=nullable)
    assert field.validate(value) == expected


@pytest.mark.parametrize(
    "nullable, value",
    [
        (False, {}),
        (False, None),
        (True, []),
        (True, "text"),
        (True, 123),
    ],
    ids=[
        "False_empty",
        "False_None",
        "True_empty_list",
        "True_text",
        "True_123",
    ],
)
def test_arguments_field_reject_invalid(nullable, value):
    field = ArgumentsField(nullable=nullable)
    with pytest.raises(ValueError):
        field.validate(value)


# Проверка EmailField
@pytest.mark.parametrize(
    "nullable, value, expected",
    [
        (False, "user@example.com", "user@example.com"),
        (False, "@", "@"),
        (True, None, None),
        (True, "", ""),
    ],
    ids=[
        "not_nullable_user@example.com",
        "not_nullable_@",
        "nullable_None",
        "nullable_empty",
    ],
)
def test_email_field_validate(nullable, value, expected):
    field = EmailField(nullable=nullable)
    assert field.validate(value) == expected


@pytest.mark.parametrize(
    "nullable, value",
    [
        (False, None),
        (False, ""),
        (False, "example.com"),
        (True, "example.com"),
        (True, 123),
    ],
    ids=[
        "not_nullable_None",
        "not_nullable_empty",
        "not_nullable_example.com",
        "nullable_example.com",
        "nullable_123",
    ],
)
def test_email_field_reject_invalid(nullable, value):
    field = EmailField(nullable=nullable)
    with pytest.raises(ValueError):
        field.validate(value)


# Проверка PhoneField
@pytest.mark.parametrize(
    "nullable, value, expected",
    [
        (False, "79990000000", "79990000000"),
        (False, 79990000000, "79990000000"),
        (True, None, None),
        (True, "", ""),
    ],
)
def test_phone_field_validate(nullable, value, expected):
    field = PhoneField(nullable=nullable)
    assert field.validate(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "7999000000",
        "799900000000",
        "89990000000",
        "7999000000a",
        "7９９９０００００００",
        True,
        79990000000.0,
        None,
        "",
    ],
    ids=[
        "too_short",
        "too_long",
        "wrong_prefix",
        "letter",
        "non_ascii_digits",
        "bool",
        "float",
        "none",
        "empty",
    ],
)
def test_phone_field_reject_invalid(value):
    with pytest.raises(ValueError):
        PhoneField().validate(value)


# Проверка DateField
@pytest.mark.parametrize(
    "nullable, value, expected",
    [
        (False, "01.01.2000", date(2000, 1, 1)),
        (False, "29.02.2024", date(2024, 2, 29)),
        (True, None, None),
        (True, "", ""),
    ],
    ids=["date", "leap_day", "nullable_none", "nullable_empty"],
)
def test_date_field_validate(nullable, value, expected):
    assert DateField(nullable=nullable).validate(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "1.01.2000",
        "01.1.2000",
        "2000-01-01",
        "29.02.2023",
        "31.04.2024",
        "01.13.2024",
        123,
        date(2000, 1, 1),
        None,
        "",
    ],
    ids=[
        "short_day",
        "short_month",
        "wrong_format",
        "invalid_leap_day",
        "invalid_day",
        "invalid_month",
        "integer",
        "date_object",
        "none",
        "empty",
    ],
)
def test_date_field_reject_invalid(value):
    with pytest.raises(ValueError):
        DateField().validate(value)


# Проверка BirthDayField
@pytest.fixture
def frozen_today(monkeypatch):
    """Фиксирует текущую дату для проверки границ возраста."""

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 7)

    monkeypatch.setattr("api.datetime.date", FixedDate)
    return FixedDate.today()


@pytest.mark.parametrize(
    "nullable, value, expected",
    [
        (False, "07.10.2026", date(2026, 10, 7)),
        (False, "07.10.1956", date(1956, 10, 7)),
        (False, "08.10.1955", date(1955, 10, 8)),
        (False, "29.02.2000", date(2000, 2, 29)),
        (True, None, None),
        (True, "", ""),
    ],
    ids=[
        "born_today",
        "exactly_70",
        "almost_71",
        "leap_day",
        "nullable_none",
        "nullable_empty",
    ],
)
def test_birthday_field_validate(frozen_today, nullable, value, expected):
    assert BirthDayField(nullable=nullable).validate(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "08.10.2026",
        "07.10.1955",
        "06.10.1955",
        "29.02.2023",
        "2000-01-01",
        123,
        None,
        "",
    ],
    ids=[
        "tomorrow",
        "exactly_71",
        "over_71",
        "invalid_date",
        "wrong_format",
        "integer",
        "none",
        "empty",
    ],
)
def test_birthday_field_reject_invalid(frozen_today, value):
    with pytest.raises(ValueError):
        BirthDayField().validate(value)


# Проверка GenderField
@pytest.mark.parametrize(
    "nullable, value",
    [(False, 0), (False, 1), (False, 2), (True, None), (True, "")],
    ids=["zero", "one", "two", "nullable_none", "nullable_empty"],
)
def test_gender_field_validate(nullable, value):
    result = GenderField(nullable=nullable).validate(value)
    assert result == value
    assert type(result) is type(value)


@pytest.mark.parametrize(
    "value",
    [-1, 3, "1", True, False, 1.0, [], None, ""],
    ids=[
        "below_range",
        "above_range",
        "string",
        "true",
        "false",
        "float",
        "list",
        "none",
        "empty",
    ],
)
def test_gender_field_reject_invalid(value):
    with pytest.raises(ValueError):
        GenderField().validate(value)


# Проверка ClientIDsField
@pytest.mark.parametrize(
    "nullable, value",
    [
        (False, [1, 2]),
        (False, [0]),
        (False, [1, 1]),
        (True, []),
        (True, None),
    ],
    ids=["integers", "zero", "duplicates", "nullable_empty", "nullable_none"],
)
def test_client_ids_field_validate(nullable, value):
    assert ClientIDsField(nullable=nullable).validate(value) == value


@pytest.mark.parametrize(
    "value",
    [["1"], [1, "2"], [True], [1.0], (1, 2), {"id": 1}, "1", [], None],
    ids=[
        "string_item",
        "mixed_types",
        "bool_item",
        "float_item",
        "tuple",
        "dict",
        "string",
        "empty",
        "none",
    ],
)
def test_client_ids_field_reject_invalid(value):
    with pytest.raises(ValueError):
        ClientIDsField().validate(value)
