import socket
from email.utils import parsedate_to_datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import httpd

from httpd import (
    build_response,
    get_content_type,
    parse_request_line,
    receive_headers,
    resolve_path,
    handle_request,
    parse_args,
)


@pytest.fixture
def socket_pair():
    # Два соединённых сокета заменяют клиента и сервер без открытия TCP-порта.
    sender, receiver = socket.socketpair()
    with sender, receiver:
        receiver.settimeout(0.1)
        # После теста with закроет оба сокета, даже если проверка упадёт.
        yield sender, receiver


def test_receive_headers_collects_fragments_and_discards_tail():
    # Каждый recv вернёт очередную порцию; конец заголовков разрезан между
    # ними.
    connection = Mock()
    connection.gettimeout.return_value = None
    connection.recv.side_effect = [
        b"GET / HTTP/1.1\r\nHost: local",
        b"host\r\n\r",
        b"\nEXTRA",
    ]

    # Заголовки должны собраться целиком, а байты EXTRA не должны попасть в
    # результат.
    assert (
        receive_headers(connection)
        == b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
    )


def test_receive_headers_rejects_incomplete_headers(socket_pair):
    # Клиент завершает отправку, не прислав пустую строку в конце заголовков.
    sender, receiver = socket_pair
    sender.sendall(b"GET / HTTP/1.1\r\n")
    sender.shutdown(socket.SHUT_WR)

    with pytest.raises(ValueError, match="Соединение завершено"):
        receive_headers(receiver)


def test_receive_headers_accepts_exact_limit(socket_pair):
    # Размер включает CRLFCRLF; точное совпадение с лимитом разрешено.
    sender, receiver = socket_pair
    headers = b"GET / HTTP/1.1\r\n\r\n"
    sender.sendall(headers)

    assert receive_headers(receiver, len(headers)) == headers


def test_receive_headers_rejects_exceeded_limit(socket_pair):
    # До полного конца заголовков не хватает одного разрешённого байта.
    sender, receiver = socket_pair
    headers = b"GET / HTTP/1.1\r\n\r\n"
    sender.sendall(headers)

    with pytest.raises(ValueError, match="Превышен лимит"):
        receive_headers(receiver, len(headers) - 1)


def test_receive_headers_times_out_for_silent_open_connection(socket_pair):
    # Соединение остаётся открытым, но данных нет: ждём таймаут, а не EOF.
    _, receiver = socket_pair

    with pytest.raises(TimeoutError):
        receive_headers(receiver)


@pytest.mark.parametrize("original_timeout", [None, 3.0])
@pytest.mark.parametrize("outcome", ["success", "eof", "timeout"])
def test_headers_restore_socket_timeout(
    monkeypatch, original_timeout, outcome
):
    # После чтения или ошибки отправка ответа получает прежний таймаут.
    connection = Mock()
    connection.gettimeout.return_value = original_timeout
    monkeypatch.setattr(
        httpd, "time", SimpleNamespace(monotonic=lambda: 100.0)
    )
    if outcome == "success":
        connection.recv.return_value = b"GET / HTTP/1.1\r\n\r\n"
        assert receive_headers(connection, header_timeout=5.0)
    else:
        if outcome == "eof":
            connection.recv.return_value = b""
            expected = ValueError
        else:
            connection.recv.side_effect = TimeoutError("test timeout")
            expected = TimeoutError
        with pytest.raises(expected):
            receive_headers(connection, header_timeout=5.0)

    applied = connection.settimeout.call_args_list
    assert applied[0].args[0] == (
        5.0 if original_timeout is None else original_timeout
    )
    assert applied[-1].args[0] == original_timeout


def test_headers_fragments_do_not_extend_deadline(monkeypatch):
    # Часы подменены: тест проверяет общий срок без настоящего ожидания.
    clock = Mock(side_effect=[100.0, 100.1, 100.6, 101.1])
    monkeypatch.setattr(httpd, "time", SimpleNamespace(monotonic=clock))
    connection = Mock()
    connection.gettimeout.return_value = 5.0
    connection.recv.side_effect = [b"GET ", b"/ "]

    with pytest.raises(TimeoutError, match="Истекло время"):
        receive_headers(connection, header_timeout=1.0)

    # Третий recv уже не должен начаться; срок не продлевается порциями.
    assert connection.recv.call_count == 2
    values = [call.args[0] for call in connection.settimeout.call_args_list]
    assert values == pytest.approx([0.9, 0.4, 5.0])


def test_headers_deadline_limits_real_socket_and_restores_timeout(socket_pair):
    # Исходный таймаут больше дедлайна: молчание ограничивается общим сроком.
    _, receiver = socket_pair
    receiver.settimeout(2.0)
    with pytest.raises(TimeoutError):
        receive_headers(receiver, header_timeout=0.02)
    assert receiver.gettimeout() == 2.0


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_parse_request_line_returns_three_parts(method):
    # Разбор POST допустим: решение ответить 405 принимает обработчик, не
    # парсер.
    headers = (
        f"{method} /index.html HTTP/1.1\r\nHost: localhost\r\n\r\n".encode(
            "ascii"
        )
    )

    assert parse_request_line(headers) == (method, "/index.html", "HTTP/1.1")


def test_parse_request_line_rejects_missing_version():
    # Без версии строка содержит только две обязательные части вместо трёх.
    with pytest.raises(ValueError):
        parse_request_line(b"GET /index.html\r\n\r\n")


@pytest.mark.parametrize(
    "line",
    [
        b"GET / BANANA",
        b"GET / HTTP/1x1",
        b"GET / HTTP/1.10",
        b"GET / http/1.1",
        b"G(ET / HTTP/1.1",
        b"GET /bad\x00name HTTP/1.1",
        b"GET /bad\tname HTTP/1.1",
        b"GET  / HTTP/1.1",
        b"GET  HTTP/1.1",
        b"GET\t / HTTP/1.1",
        b"GET / HTTP/1.1\t",
        b"GET /\xff HTTP/1.1",
    ],
)
def test_request_line_rejects_invalid_syntax(line):
    # Пробелы и управляющие символы нельзя незаметно удалить через split().
    with pytest.raises(ValueError):
        parse_request_line(line + b"\r\n\r\n")


@pytest.mark.parametrize("version", ["HTTP/1.0", "HTTP/1.1", "HTTP/2.0"])
def test_request_line_checks_version_syntax_only(version):
    # Поддержку версии проверит обработчик, поэтому форма HTTP/2.0 допустима.
    line = f"POST /my%20file.html?q=1 {version}\r\n\r\n".encode("ascii")
    assert parse_request_line(line) == ("POST", "/my%20file.html?q=1", version)


@pytest.fixture
def document_root(tmp_path):
    # Каждый тест получает свой каталог; настоящая папка www проекта не
    # меняется.
    root = tmp_path / "www"
    (root / "guide").mkdir(parents=True)
    (root / "index.html").write_bytes(b"home")
    (root / "guide" / "index.html").write_bytes(b"guide")
    return root.resolve()


@pytest.mark.parametrize(
    ("target", "relative_path"),
    [
        ("/", "index.html"),
        ("/guide/", "guide/index.html"),
        ("/images/cat.png", "images/cat.png"),
        ("/my%20file.html?download=1", "my file.html"),
    ],
)
def test_resolve_path_selects_resource(document_root, target, relative_path):
    # Проверяем индексы каталогов, обычный путь, декодирование пробела и
    # удаление query.
    # Обычные файлы здесь могут отсутствовать: функция пока только выбирает
    # путь.
    assert resolve_path(target, document_root) == document_root / relative_path


@pytest.mark.parametrize("target", ["/../secret.txt", "/%2e%2e/secret.txt"])
def test_resolve_path_rejects_escape_from_root(document_root, target):
    # Обычный и закодированный переход к родителю не должны выходить за корень.
    with pytest.raises(ValueError):
        resolve_path(target, document_root)


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("index.html", "text/html"),
        ("style.css", "text/css"),
        ("app.js", "application/javascript"),
        ("photo.jpg", "image/jpeg"),
        ("photo.jpeg", "image/jpeg"),
        ("photo.JPG", "image/jpeg"),
        ("image.png", "image/png"),
        ("image.gif", "image/gif"),
        ("animation.swf", "application/x-shockwave-flash"),
        ("data.unknown", "application/octet-stream"),
    ],
)
def test_get_content_type(filename, content_type):
    # Тип определяется по имени, включая верхний регистр и неизвестное
    # расширение.
    assert get_content_type(Path(filename)) == content_type


@pytest.mark.parametrize(
    ("body", "content_type"),
    [(b"hello", "text/plain"), (b"\x00\xff", "application/octet-stream")],
)
def test_build_response_preserves_body_and_required_headers(
    body, content_type
):
    # Одна проверка применяется к тексту и к байтам, которые нельзя
    # декодировать как ASCII.
    response = build_response(200, body, content_type)
    raw_headers, actual_body = response.split(b"\r\n\r\n", 1)
    # Декодируем только заголовки; тело оставляем байтами и сравниваем без
    # преобразований.
    status_line, *lines = raw_headers.decode("ascii").split("\r\n")
    headers = dict(line.split(": ", 1) for line in lines)

    assert status_line == "HTTP/1.1 200 OK"
    assert actual_body == body
    assert headers["Content-Length"] == str(len(body))
    assert headers["Content-Type"] == content_type
    assert headers["Connection"] == "close"
    assert headers["Server"]
    # Дата должна разбираться стандартной библиотекой и иметь нулевое смещение
    # от UTC.
    assert (
        parsedate_to_datetime(headers["Date"]).utcoffset().total_seconds() == 0
    )


@pytest.mark.parametrize("status_code", [200, 404])
def test_build_response_for_head_omits_body_but_preserves_length(status_code):
    # Даже для ошибки HEAD не передаёт тело, но сохраняет размер
    # соответствующего GET.
    response = build_response(
        status_code, b"hello", "text/plain", head_only=True
    )
    headers, body = response.split(b"\r\n\r\n", 1)

    assert b"Content-Length: 5" in headers.split(b"\r\n")
    assert body == b""


@pytest.mark.parametrize(
    ("status_code", "reason"),
    [(403, "Forbidden"), (404, "Not Found"), (405, "Method Not Allowed")],
)
def test_build_response_uses_error_status(status_code, reason):
    # Проверяем код и описание ошибки в первой строке HTTP-ответа.
    response = build_response(status_code, b"error", "text/plain")

    assert response.split(b"\r\n", 1)[
        0
    ] == f"HTTP/1.1 {status_code} {reason}".encode("ascii")
    if status_code == 405:
        # Ответ 405 также сообщает список поддерживаемых методов.
        headers = response.split(b"\r\n\r\n", 1)[0]
        assert b"Allow: GET, HEAD" in headers.split(b"\r\n")


def exchange_request(request: bytes, document_root: Path) -> bytes:
    # Вспомогательная функция для маленьких запросов и ответов в интеграционных
    # тестах.
    sender, receiver = socket.socketpair()

    with sender, receiver:
        sender.settimeout(1)
        receiver.settimeout(1)

        sender.sendall(request)
        # Обработчик отправит ответ и закроет receiver через свой with.
        handle_request(receiver, document_root)

        response = b""

        while True:
            chunk = sender.recv(4096)
            # Сначала читаем все доступные байты; затем закрытое соединение
            # даст b"".
            if chunk == b"":
                break
            response += chunk

        return response


@pytest.mark.parametrize(
    ("method", "expected_body"),
    [("GET", b"home"), ("HEAD", b"")],
)
def test_handle_request_get_and_head(document_root, method, expected_body):
    # Фикстура создала index.html с четырьмя байтами b"home".
    request = (
        f"{method} /index.html HTTP/1.1\r\n" "Host: localhost\r\n\r\n"
    ).encode("ascii")

    response = exchange_request(request, document_root)
    raw_headers, body = response.split(b"\r\n\r\n", 1)
    status_line, *lines = raw_headers.decode("ascii").split("\r\n")
    headers = dict(line.split(": ", 1) for line in lines)

    # Проверяем совместную работу чтения запроса, поиска файла и сборки ответа.
    assert status_line == "HTTP/1.1 200 OK"
    assert headers["Content-Type"] == "text/html"
    assert headers["Content-Length"] == "4"
    assert headers["Connection"] == "close"
    # Для HEAD длина остаётся равной 4, но фактическое тело должно быть пустым.
    assert body == expected_body


def test_handle_request_rejects_unsupported_method(document_root):
    # Файла нет, но проверка метода должна сработать раньше поиска: нужен 405,
    # не 404.
    request = b"POST /missing.html HTTP/1.1\r\nHost: localhost\r\n\r\n"

    response = exchange_request(request, document_root)
    raw_headers, body = response.split(b"\r\n\r\n", 1)
    status_line, *lines = raw_headers.decode("ascii").split("\r\n")
    headers = dict(line.split(": ", 1) for line in lines)

    assert status_line == "HTTP/1.1 405 Method Not Allowed"
    assert headers["Allow"] == "GET, HEAD"
    assert headers["Content-Type"] == "text/plain"
    # POST не является HEAD: текст ошибки действительно должен передаваться.
    assert body == b"Unknown method"
    assert headers["Content-Length"] == str(len(body))


def test_parse_args_uses_default_host_and_port(document_root, monkeypatch):
    # Разбираем относительный путь из временной рабочей папки, не запуская
    # сервер.
    monkeypatch.chdir(document_root.parent)

    args = parse_args(["-r", document_root.name])

    assert args.host == "127.0.0.1"
    assert args.port == 8080
    # Без --threads используется пул из четырёх рабочих потоков.
    assert args.threads == 4
    # В результат должен вернуться нормализованный абсолютный Path.
    assert args.document_root == document_root
    assert args.document_root.is_absolute()


def test_parse_args_uses_explicit_host_and_port(document_root):
    # Переданный список заменяет аргументы терминала только для этого вызова.
    args = parse_args(
        [
            "-r",
            str(document_root),
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--threads",
            "2",
        ]
    )

    assert args.host == "0.0.0.0"
    assert args.port == 9000
    # Проверяем передачу размера пула из строки команды в целое число.
    assert args.threads == 2
    assert args.document_root == document_root


@pytest.mark.parametrize("port", ["0", "65536", "abc"])
def test_parse_args_rejects_invalid_port(document_root, port):
    # Числа вне диапазона и нечисловой ввод отклоняются до открытия сокета.
    with pytest.raises(SystemExit) as error:
        parse_args(["-r", str(document_root), "--port", port])

    # argparse завершает разбор неверной команды с кодом 2.
    assert error.value.code == 2


def test_parse_args_rejects_missing_directory(tmp_path):
    # tmp_path существует, но его дочернюю папку missing мы не создавали.
    with pytest.raises(SystemExit) as error:
        parse_args(["-r", str(tmp_path / "missing")])

    assert error.value.code == 2


@pytest.mark.parametrize("threads", ["0", "-1", "abc"])
def test_parse_args_rejects_invalid_thread_count(document_root, threads):
    # Пул требует хотя бы один поток; нечисловой ввод отклоняет type=int.
    with pytest.raises(SystemExit) as error:
        parse_args(["-r", str(document_root), "--threads", threads])

    assert error.value.code == 2


@pytest.mark.parametrize(
    ("options", "expected"),
    [([], 1), (["-w", "2"], 2), (["--workers", "3"], 3)],
)
def test_parse_args_worker_count(document_root, options, expected):
    # Проверяем значение по умолчанию и оба имени параметра процессов.
    args = parse_args(["-r", str(document_root), *options])
    assert args.workers == expected


@pytest.mark.parametrize("workers", ["0", "-1", "abc"])
def test_parse_args_rejects_invalid_worker_count(document_root, workers):
    # Неверное число процессов отклоняется ещё до создания сервера.
    with pytest.raises(SystemExit) as error:
        parse_args(["-r", str(document_root), "-w", workers])
    assert error.value.code == 2
