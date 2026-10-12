"""Проверки обработчиков API без запуска HTTP-сервера."""

import datetime
import functools
import hashlib
import unittest
from copy import deepcopy
from unittest.mock import Mock

import api
from store import Store


def cases(cases):
    """Запускает наборы данных с отдельным subTest для каждого случая."""

    def decorator(f):
        """Создаёт обёртку тестового метода."""

        @functools.wraps(f)
        def wrapper(*args):
            """Вызывает тест для каждого набора данных с копией входа."""
            for index, case in enumerate(cases):
                with args[0].subTest(case=index, data=case):
                    data = deepcopy(case)
                    new_args = args + (data if isinstance(data, tuple) else (data,))
                    f(*new_args)

        return wrapper

    return decorator


class TestSuite(unittest.TestCase):
    """Проверки запросов, авторизации и результатов методов API."""

    def setUp(self):
        """Создаёт контекст, заголовки и Mock хранилища."""
        self.context = {}
        self.headers = {}
        self.store = Mock(spec=Store)
        self.store.cache_get.return_value = None
        self.store.cache_set.return_value = True
        self.store.get.return_value = '["books", "music"]'

    def get_response(self, request):
        """Очищает контекст и вызывает method_handler."""
        self.context.clear()
        self.store.reset_mock()
        return api.method_handler(
            {"body": request, "headers": self.headers}, self.context, self.store
        )

    def set_valid_auth(self, request):
        """Добавляет правильный токен в словарь запроса."""
        if request.get("login") == api.ADMIN_LOGIN:
            request["token"] = hashlib.sha512(
                (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode(
                    "utf-8"
                )
            ).hexdigest()
        else:
            msg = (
                request.get("account", "") + request.get("login", "") + api.SALT
            ).encode("utf-8")
            request["token"] = hashlib.sha512(msg).hexdigest()

    def test_empty_request(self):
        _, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)

    @cases(
        [
            {
                "account": "horns&hoofs",
                "login": "h&f",
                "method": "online_score",
                "token": "",
                "arguments": {},
            },
            {
                "account": "horns&hoofs",
                "login": "h&f",
                "method": "online_score",
                "token": "sdd",
                "arguments": {},
            },
            {
                "account": "horns&hoofs",
                "login": "admin",
                "method": "online_score",
                "token": "",
                "arguments": {},
            },
        ]
    )
    def test_bad_auth(self, request):
        _, code = self.get_response(request)
        self.assertEqual(api.FORBIDDEN, code)

    @cases(
        [
            {"account": "horns&hoofs", "login": "h&f", "method": "online_score"},
            {"account": "horns&hoofs", "login": "h&f", "arguments": {}},
            {"account": "horns&hoofs", "method": "online_score", "arguments": {}},
        ]
    )
    def test_invalid_method_request(self, request):
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertTrue(len(response))

    @cases(
        [
            {},
            {"phone": "79175002040"},
            {"phone": "89175002040", "email": "stupnikov@otus.ru"},
            {"phone": "79175002040", "email": "stupnikovotus.ru"},
            {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": -1},
            {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": "1"},
            {
                "phone": "79175002040",
                "email": "stupnikov@otus.ru",
                "gender": 1,
                "birthday": "01.01.1890",
            },
            {
                "phone": "79175002040",
                "email": "stupnikov@otus.ru",
                "gender": 1,
                "birthday": "XXX",
            },
            {
                "phone": "79175002040",
                "email": "stupnikov@otus.ru",
                "gender": 1,
                "birthday": "01.01.2000",
                "first_name": 1,
            },
            {
                "phone": "79175002040",
                "email": "stupnikov@otus.ru",
                "gender": 1,
                "birthday": "01.01.2000",
                "first_name": "s",
                "last_name": 2,
            },
            {"phone": "79175002040", "birthday": "01.01.2000", "first_name": "s"},
            {"email": "stupnikov@otus.ru", "gender": 1, "last_name": 2},
        ]
    )
    def test_invalid_score_request(self, arguments):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "online_score",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases(
        [
            ({"phone": "79175002040", "email": "stupnikov@otus.ru"}, 3.0),
            ({"phone": 79175002040, "email": "stupnikov@otus.ru"}, 3.0),
            (
                {
                    "gender": 1,
                    "birthday": "01.01.2000",
                    "first_name": "a",
                    "last_name": "b",
                },
                2.0,
            ),
            ({"gender": 0, "birthday": "01.01.2000"}, 1.5),
            ({"gender": 2, "birthday": "01.01.2000"}, 1.5),
            ({"first_name": "a", "last_name": "b"}, 0.5),
            (
                {
                    "phone": "79175002040",
                    "email": "stupnikov@otus.ru",
                    "gender": 1,
                    "birthday": "01.01.2000",
                    "first_name": "a",
                    "last_name": "b",
                },
                5.0,
            ),
        ]
    )
    def test_ok_score_request(self, arguments, expected):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "online_score",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        score = response.get("score")
        self.assertEqual(score, expected, arguments)
        self.assertEqual(sorted(self.context["has"]), sorted(arguments.keys()))

    def test_ok_score_admin_request(self):
        arguments = {"phone": "79175002040", "email": "stupnikov@otus.ru"}
        request = {
            "account": "horns&hoofs",
            "login": "admin",
            "method": "online_score",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        score = response.get("score")
        self.assertEqual(score, 42)
        self.store.cache_get.assert_not_called()
        self.store.cache_set.assert_not_called()

    @cases(
        [
            {},
            {"date": "20.07.2017"},
            {"client_ids": [], "date": "20.07.2017"},
            {"client_ids": {1: 2}, "date": "20.07.2017"},
            {"client_ids": ["1", "2"], "date": "20.07.2017"},
            {"client_ids": [1, 2], "date": "XXX"},
        ]
    )
    def test_invalid_interests_request(self, arguments):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "clients_interests",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases(
        [
            {
                "client_ids": [1, 2, 3],
                "date": datetime.datetime.today().strftime("%d.%m.%Y"),
            },
            {"client_ids": [1, 2], "date": "19.07.2017"},
            {"client_ids": [0]},
        ]
    )
    def test_ok_interests_request(self, arguments):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "clients_interests",
            "arguments": arguments,
        }
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertTrue(
            all(
                v
                and isinstance(v, list)
                and all(isinstance(i, (bytes, str)) for i in v)
                for v in response.values()
            )
        )
        self.assertEqual(self.context.get("nclients"), len(arguments["client_ids"]))
        self.assertEqual(
            response,
            {client_id: ["books", "music"] for client_id in arguments["client_ids"]},
        )

    def test_unknown_method(self):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "unknown",
            "arguments": {},
        }
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.NOT_FOUND, code)
        self.assertEqual("Unknown method", response)

    def test_duplicate_clients_ids(self):
        request = {
            "account": "horns&hoofs",
            "login": "h&f",
            "method": "clients_interests",
            "arguments": {
                "client_ids": [1, 1, 2],
            },
        }
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        self.assertEqual({1, 2}, set(response))
        self.assertEqual(3, self.context["nclients"])


if __name__ == "__main__":
    unittest.main()
