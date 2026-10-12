"""HTTP API: проверка запросов, авторизация и ответы в JSON."""

import datetime
import hashlib
import json
import logging
import re
import sys
import uuid
from argparse import ArgumentParser
from email.message import Message
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, cast

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from scoring import get_interests, get_score
from store import Store


class Gender(Enum):
    """Коды пола: 0 - неизвестен, 1 - мужской и 2 - женский."""

    UNKNOWN = 0
    MALE = 1
    FEMALE = 2


class ErrorMessage(Enum):
    """Сообщения для кодов ошибок HTTP."""

    BAD_REQUEST = "Bad Request"
    FORBIDDEN = "Forbidden"
    NOT_FOUND = "Not Found"
    INVALID_REQUEST = "Invalid Request"
    INTERNAL_ERROR = "Internal Server Error"


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"

OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500

ERRORS = {
    BAD_REQUEST: ErrorMessage.BAD_REQUEST.value,
    FORBIDDEN: ErrorMessage.FORBIDDEN.value,
    NOT_FOUND: ErrorMessage.NOT_FOUND.value,
    INVALID_REQUEST: ErrorMessage.INVALID_REQUEST.value,
    INTERNAL_ERROR: ErrorMessage.INTERNAL_ERROR.value,
}


class Field:
    """Общие проверки обязательности и пустого значения поля."""

    def __init__(self, required: bool = False, nullable: bool = False):
        self.required = required
        self.nullable = nullable

    def is_empty(self, value) -> bool:
        if value in ("", None):
            return True

        return False

    def validate_value(self, value):
        """Проверяется в подклассе для каждого типа поля."""
        raise NotImplementedError()

    def validate(self, value):
        if self.is_empty(value):
            if self.nullable:
                return value
            raise ValueError("Value cannot be null")

        return self.validate_value(value)


class CharField(Field):
    """Строковое поле."""

    def validate_value(self, value):
        if not isinstance(value, str):
            raise ValueError("Value must be a string")

        return value


class ArgumentsField(Field):
    """Словарь аргументов метода API."""

    def is_empty(self, value) -> bool:
        if value in ({}, None):
            return True

        return False

    def validate_value(self, value):
        if not isinstance(value, dict):
            raise ValueError("Value must be a dictionary")

        return value


class EmailField(CharField):
    def validate_value(self, value):
        value = super().validate_value(value)

        if "@" not in value:
            raise ValueError("Value must be a valid email address")

        return value


class PhoneField(Field):
    """Телефон из 11 цифр с первой цифрой 7."""

    def validate_value(self, value):
        if type(value) not in (str, int):
            raise ValueError("Value must be a string or integer")

        value = str(value)

        if (
            not value.startswith("7")
            or len(value) != 11
            or not all("0" <= char <= "9" for char in value)
        ):
            raise ValueError("Value must be phone number")

        return value


class DateField(Field):
    """Дата в формате DD.MM.YYYY."""

    def validate_value(self, value):
        if not isinstance(value, str):
            raise ValueError("Value must be a string")

        if re.fullmatch(r"[0-9]{2}\.[0-9]{2}\.[0-9]{4}", value) is None:
            raise ValueError("Value must use DD.MM.YYYY format")

        value = datetime.datetime.strptime(value, "%d.%m.%Y").date()

        return value


class BirthDayField(DateField):
    """Дата рождения с возрастом не больше 70 полных лет."""

    def validate_value(self, value):
        """Проверяет дату рождения, возраст и отсутствие будущей даты."""
        value = super().validate_value(value)
        today = datetime.date.today()

        if value > today:
            raise ValueError("Birth date cannot be in the future")

        age = today.year - value.year

        if (today.month, today.day) < (value.month, value.day):
            age -= 1

        if age > 70:
            raise ValueError("Age must not > 70")

        return value


class GenderField(Field):
    """Целочисленный код пола: 0, 1 или 2."""

    def validate_value(self, value):
        """Принимает целые 0, 1 и 2, но не bool."""
        if value not in (0, 1, 2) or type(value) is not int:
            raise ValueError("Value must be 0, 1 or 2")

        return value


class ClientIDsField(Field):
    """Список целочисленных ID клиентов."""

    def is_empty(self, value) -> bool:
        """Проверяет None и пустой список."""
        if value in ([], None):
            return True

        return False

    def validate_value(self, value):
        """Проверяет список целых чисел без bool."""
        if not isinstance(value, list) or not all(type(item) is int for item in value):
            raise ValueError("Value must be a list and all elements are int")

        return value


class BaseRequest:
    """Проверяет поля запроса и сохраняет значения и ошибки."""

    @classmethod
    def get_fields(cls):
        """Собирает поля класса и родителей с учётом переопределений."""
        attributes = {}

        for base in reversed(cls.__mro__):
            attributes.update(vars(base))

        fields = {}

        for key, value in attributes.items():
            if isinstance(value, Field):
                fields[key] = value

        return fields

    def __init__(self, data):
        """Проверяет входные поля и записывает ошибки в errors."""
        self.data = data
        self.errors = {}

        for name, field in self.get_fields().items():
            setattr(self, name, None)

            if name not in data:
                if field.required:
                    self.errors[name] = "This field is required."
            else:
                try:
                    value = field.validate(data[name])
                except ValueError as error:
                    self.errors[name] = str(error)
                else:
                    setattr(self, name, value)


class ClientsInterestsRequest(BaseRequest):
    """Запрос интересов с обязательным списком ID клиентов."""

    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(BaseRequest):
    """Запрос оценки с хотя бы одной полной парой аргументов."""

    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, data):
        """Проверяет поля и пары аргументов, включая gender=0."""
        super().__init__(data)

        if self.errors:
            return

        has_contacts = self.phone not in (None, "") and self.email not in (None, "")

        has_name = self.first_name not in (None, "") and self.last_name not in (
            None,
            "",
        )

        has_birth_info = self.birthday not in (None, "") and self.gender not in (
            None,
            "",
        )

        if not (has_contacts or has_name or has_birth_info):
            self.errors["arguments"] = (
                "At least one complete pair is required: "
                "phone/email, first_name/last_name, gender/birthday"
            )


class MethodRequest(BaseRequest):
    """Аккаунт, логин, токен, метод и аргументы запроса."""

    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=True)

    @property
    def is_admin(self) -> bool:
        """Проверяет, указан ли логин admin."""
        return self.login == ADMIN_LOGIN


def check_auth(request: MethodRequest) -> bool:
    """Проверяет токен пользователя или часовой токен admin."""
    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")
        ).hexdigest()
    else:
        account = cast(str | None, cast(object, request.account)) or ""
        login = cast(str | None, cast(object, request.login)) or ""

        digest = hashlib.sha512((account + login + SALT).encode("utf-8")).hexdigest()
    return digest == request.token


def method_handler(
    request: dict[str, Any],
    ctx: dict[str, Any],
    store,
) -> tuple[dict[str, Any] | str, int]:
    """Проверяет запрос и авторизацию, затем вызывает обработчик метода."""
    body = request.get("body")

    if not isinstance(body, dict):
        return "Body must be dict", INVALID_REQUEST

    method_request = MethodRequest(body)

    if method_request.errors:
        return method_request.errors, INVALID_REQUEST

    if not check_auth(method_request):
        return "Forbidden", FORBIDDEN

    if method_request.method == "online_score":
        return handle_online_score(method_request, ctx, store)
    elif method_request.method == "clients_interests":
        return handle_clients_interests(method_request, ctx, store)
    else:
        return "Unknown method", NOT_FOUND


def handle_online_score(
    method_request,
    ctx,
    store,
):
    """Возвращает оценку и код ответа, записывает заполненные поля в ctx."""
    arguments = method_request.arguments

    if arguments is None:
        arguments = {}

    score_request = OnlineScoreRequest(arguments)

    if score_request.errors:
        return score_request.errors, INVALID_REQUEST

    ctx["has"] = []

    for name, field in score_request.get_fields().items():
        value = getattr(score_request, name)

        if not field.is_empty(value):
            ctx["has"].append(name)

    if method_request.is_admin:
        score = 42
    else:
        score = get_score(
            phone=score_request.phone,
            email=score_request.email,
            birthday=score_request.birthday,
            gender=score_request.gender,
            first_name=score_request.first_name,
            last_name=score_request.last_name,
            store=store,
        )

    return {"score": score}, OK


def handle_clients_interests(
    method_request,
    ctx,
    store,
):
    """Возвращает интересы по ID и записывает число ID в ctx."""
    arguments = method_request.arguments

    if arguments is None:
        arguments = {}

    clients_request = ClientsInterestsRequest(arguments)

    if clients_request.errors:
        return clients_request.errors, INVALID_REQUEST

    client_ids = cast(list[int], cast(object, clients_request.client_ids))

    ctx["nclients"] = len(client_ids)

    client_interests = {}

    for client_id in client_ids:
        interests = get_interests(store, client_id)

        client_interests[client_id] = interests

    return client_interests, OK


class MainHTTPHandler(BaseHTTPRequestHandler):
    """Обрабатывает POST-запросы и отправляет ответы в JSON."""

    router: dict[str, Callable] = {"method": method_handler}

    def get_request_id(self, headers: Message[str, str]) -> str:
        """Берёт ID запроса из заголовка или создаёт новый."""
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self) -> None:
        """Читает JSON, вызывает обработчик и отправляет ответ HTTP."""
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(data_string)
        except Exception:
            code = BAD_REQUEST

        if code == OK:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers},
                        context,
                        self.server.store,
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode("utf-8"))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()

    handler = (
        logging.FileHandler(args.log) if args.log else logging.StreamHandler(sys.stdout)
    )

    logging.basicConfig(
        handlers=[handler],
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    redis_client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        retry=Retry(NoBackoff(), 0),
    )

    store = Store(redis_client)

    server = HTTPServer(("localhost", args.port), MainHTTPHandler)
    server.store = store

    logging.info("Starting server at %s" % args.port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        redis_client.close()
