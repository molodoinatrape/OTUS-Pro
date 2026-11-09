"""Проверки ошибок, ограничителя и настоящего TCP-сервера."""

import os
import signal
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, nullcontext
from pathlib import Path
from threading import BoundedSemaphore
from unittest.mock import MagicMock, Mock

import pytest

import httpd


def read_response(connection):
    # Ответ заканчивается закрытием соединения; один recv может вернуть только
    # часть.
    result = b""
    while True:
        chunk = connection.recv(65536)
        if not chunk:
            return result
        result += chunk


def split_response(response):
    # Тело не декодируем: оно может содержать изображение или другие бинарные
    # данные.
    raw_headers, body = response.split(b"\r\n\r\n", 1)
    status, *lines = raw_headers.decode("ascii").split("\r\n")
    return status, dict(line.split(": ", 1) for line in lines), body


def request(method, target):
    return f"{method} {target} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode(
        "ascii"
    )


@pytest.fixture
def root(tmp_path):
    # Файлы принадлежат только тесту и не меняют учебную папку www.
    result = tmp_path / "www"
    result.mkdir()
    (result / "index.html").write_bytes(b"home")
    (result / "my file.html").write_bytes(b"space")
    (result / "blob.png").write_bytes(bytes(range(256)) * 512)
    (result / "guide").mkdir()
    (result / "guide" / "index.html").write_bytes(b"guide")
    (tmp_path / "secret.txt").write_bytes(b"outside")
    return result


@pytest.mark.parametrize("method", ["GET", "HEAD"])
@pytest.mark.parametrize(
    ("target", "code", "expected"),
    [
        ("/missing.html", 404, b"Not Found"),
        ("/../secret.txt", 403, b"Forbidden"),
        ("/%2e%2e/secret.txt", 403, b"Forbidden"),
        ("/index.html/child", 404, b"Not Found"),
    ],
)
def test_handler_errors_and_head(root, method, target, code, expected):
    # Проверяем весь обработчик, включая отсутствие тела ошибки у HEAD.
    client, server = socket.socketpair()
    with client, server:
        client.settimeout(1)
        server.settimeout(1)
        client.sendall(request(method, target))
        httpd.handle_request(server, root)
        status, headers, body = split_response(read_response(client))
    assert status.split()[1] == str(code)
    assert int(headers["Content-Length"]) == len(expected)
    assert body == (b"" if method == "HEAD" else expected)


def test_handler_permission_error(root, monkeypatch):
    # Права Windows и POSIX различаются, поэтому отказ открытия воспроизводим
    # явно.
    def denied(path, *args, **kwargs):
        raise PermissionError("test access denied")

    monkeypatch.setattr(Path, "open", denied)
    client, server = socket.socketpair()
    with client, server:
        client.settimeout(1)
        client.sendall(request("GET", "/index.html"))
        httpd.handle_request(server, root)
        status, _, body = split_response(read_response(client))
    assert status == "HTTP/1.1 403 Forbidden"
    assert body == b"Forbidden"


@pytest.mark.parametrize("method", ["GET", "HEAD"])
@pytest.mark.parametrize("size", [0, 150000])
def test_handler_streams_file_and_head_never_reads(
    root, monkeypatch, method, size
):
    # Настоящий файл позволяет проверить размер, порции и закрытие ресурса.
    path = root / "stream.bin"
    payload = (bytes(range(256)) * 586)[:size]
    path.write_bytes(payload)
    opened = path.open("rb")
    tracked = MagicMock(wraps=opened)
    tracked.__enter__.return_value = tracked
    tracked.__exit__.side_effect = lambda *args: opened.close()
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: tracked)
    connection = MagicMock()
    connection.recv.return_value = request(method, "/stream.bin")

    try:
        httpd.handle_request(connection, root)
        assert opened.closed
    finally:
        opened.close()

    sent = [call.args[0] for call in connection.sendall.call_args_list]
    status, headers, body = split_response(b"".join(sent))
    assert status == "HTTP/1.1 200 OK"
    assert headers["Content-Length"] == str(size)
    assert body == (payload if method == "GET" else b"")
    if method == "HEAD" or size == 0:
        # HEAD узнаёт размер через fstat, но содержимое вообще не читает.
        tracked.read.assert_not_called()
        assert len(sent) == 1
    else:
        # Файл больше буфера передаётся полностью.
        # Повторных заголовков после тела быть не должно.
        assert [call.args[0] for call in tracked.read.call_args_list] == [
            65536,
            65536,
            18928,
        ]
        assert [len(chunk) for chunk in sent[1:]] == [65536, 65536, 18928]


@pytest.mark.parametrize("failure", ["early_eof", "send"])
def test_stream_failure_closes_file_without_second_response(
    root, monkeypatch, failure
):
    opened = (root / "index.html").open("rb")
    tracked = MagicMock(wraps=opened)
    tracked.__enter__.return_value = tracked
    tracked.__exit__.side_effect = lambda *args: opened.close()
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: tracked)
    connection = MagicMock()
    connection.recv.return_value = request("GET", "/index.html")
    if failure == "early_eof":
        # Файл укоротился после fstat: закрываем соединение, не дописываем 404.
        tracked.read.return_value = b""
    else:
        # Заголовки отправлены, но отправка тела завершилась ошибкой.
        connection.sendall.side_effect = [None, OSError("send failed")]

    try:
        with pytest.raises(OSError):
            httpd.handle_request(connection, root)
        assert opened.closed
    finally:
        opened.close()

    sent = [call.args[0] for call in connection.sendall.call_args_list]
    assert sent[0].startswith(b"HTTP/1.1 200 OK\r\n")
    assert not any(chunk.startswith(b"HTTP/1.1") for chunk in sent[1:])


@pytest.mark.parametrize("method", ["GET", "HEAD"])
@pytest.mark.parametrize(
    "target,expected_code", [("/index.html/", 404), ("/empty/", 404)]
)
def test_handler_matches_external_directory_rules(
    root, method, target, expected_code
):
    # Набор из ДЗ: слеш требует каталог, а отсутствие индекса даёт 404.
    (root / "empty").mkdir()
    client, server = socket.socketpair()
    with client, server:
        client.settimeout(1)
        server.settimeout(1)
        client.sendall(request(method, target))
        httpd.handle_request(server, root)
        status, _, body = split_response(read_response(client))
    assert int(status.split()[1]) == expected_code
    if method == "HEAD":
        assert body == b""


@pytest.mark.parametrize(
    "failure", [None, ValueError("bad request"), OSError("network error")]
)
def test_worker_returns_slot_after_success_or_error(
    root, monkeypatch, failure
):
    # Место освобождается ровно один раз и после успеха, и после ожидаемой
    # ошибки.
    slots = BoundedSemaphore(1)
    assert slots.acquire(blocking=False)
    monkeypatch.setattr(httpd, "handle_request", Mock(side_effect=failure))
    httpd.handle_client(Mock(), ("127.0.0.1", 1), root, slots)
    assert slots.acquire(blocking=False)
    assert not slots.acquire(blocking=False)


@pytest.mark.parametrize("value", ["0", "3"])
def test_cli_accepts_queue_size(root, value):
    # Ноль разрешён: остаются места только для рабочих потоков.
    assert httpd.parse_args(
        ["-r", str(root), "--max-queue", value]
    ).max_queue == int(value)


@pytest.mark.parametrize("value", ["-1", "abc"])
def test_cli_rejects_invalid_queue_size(root, value):
    # Ошибка конфигурации должна обнаруживаться до запуска сервера.
    with pytest.raises(SystemExit) as error:
        httpd.parse_args(["-r", str(root), "--max-queue", value])
    assert error.value.code == 2


def wait_until(condition, process, log, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        assert process.poll() is None, log.read_text(encoding="utf-8")
        time.sleep(0.01)
    pytest.fail(
        "Ожидаемое событие не наступило:\n" + log.read_text(encoding="utf-8")
    )


@pytest.fixture
def server_factory(root, tmp_path):
    # Запускаем настоящий сервер отдельным процессом; завершаем только свои
    # процессы.
    running = []

    def start(threads=2, max_queue=2, workers=1):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        log = tmp_path / f"server-{port}.log"
        stream = log.open("w", encoding="utf-8")
        process = subprocess.Popen(
            [
                sys.executable,
                "-u",
                str(Path(httpd.__file__).resolve()),
                "-r",
                str(root),
                "--port",
                str(port),
                "--threads",
                str(threads),
                "--max-queue",
                str(max_queue),
                "-w",
                str(workers),
            ],
            stdout=stream,
            stderr=subprocess.STDOUT,
            env={
                **os.environ,
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUNBUFFERED": "1",
            },
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            start_new_session=(os.name != "nt"),
        )
        running.append((process, stream))
        wait_until(
            lambda: "Сервер запущен" in log.read_text(encoding="utf-8"),
            process,
            log,
        )
        return ("127.0.0.1", port), process, log

    yield start
    for process, stream in reversed(running):
        try:
            if process.poll() is None:
                # Завершаем только собственное дерево, включая worker-детей.
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5,
                        check=False,
                    )
                else:
                    os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        finally:
            stream.close()


def accepted(log, connection):
    return str(connection.getsockname()) in log.read_text(encoding="utf-8")


def test_live_server_concurrent_clients(server_factory):
    # Быстрый клиент получает ответ, пока другой удерживает незавершённый
    # запрос.
    address, process, log = server_factory()
    with socket.create_connection(address, timeout=2) as slow:
        slow.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n")
        wait_until(lambda: accepted(log, slow), process, log)
        with socket.create_connection(address, timeout=2) as fast:
            fast.sendall(request("GET", "/"))
            assert split_response(read_response(fast))[2] == b"home"
        slow.sendall(b"\r\n")
        assert split_response(read_response(slow))[2] == b"home"


def test_live_server_bounds_admission_and_recovers_after_eof(server_factory):
    # Один worker и одно место ожидания: третье соединение не должно пройти
    # accept.
    address, process, log = server_factory(threads=1, max_queue=1)
    with ExitStack() as stack:
        slow = stack.enter_context(
            socket.create_connection(address, timeout=2)
        )
        slow.sendall(b"GET / HTTP/1.1\r\n")
        wait_until(lambda: accepted(log, slow), process, log)
        queued = stack.enter_context(
            socket.create_connection(address, timeout=2)
        )
        queued.sendall(b"GET / HTTP/1.1\r\n")
        wait_until(lambda: accepted(log, queued), process, log)
        extra = stack.enter_context(
            socket.create_connection(address, timeout=2)
        )
        extra.sendall(request("GET", "/"))
        extra.settimeout(0.2)
        with pytest.raises(TimeoutError):
            extra.recv(1)
        assert not accepted(log, extra)
        # EOF первого возвращает разрешение даже при ошибке незавершённых
        # заголовков.
        slow.shutdown(socket.SHUT_WR)
        wait_until(lambda: accepted(log, extra), process, log)
        queued.shutdown(socket.SHUT_WR)
        extra.settimeout(2)
        assert split_response(read_response(extra))[2] == b"home"


def test_live_server_keeps_slot_after_idle_accept_timeouts(server_factory):
    # Несколько пустых accept не должны постепенно расходовать все разрешения.
    address, _, _ = server_factory(threads=1, max_queue=0)
    time.sleep(1.2)
    with socket.create_connection(address, timeout=2) as client:
        client.sendall(request("GET", "/"))
        assert split_response(read_response(client))[2] == b"home"


@pytest.mark.parametrize(
    "target,expected",
    [
        ("/guide/", b"guide"),
        ("/my%20file.html?x=1", b"space"),
        ("/blob.png", bytes(range(256)) * 512),
    ],
)
def test_live_server_files_and_large_binary_body(
    server_factory, target, expected
):
    # Настоящий TCP проверяет индекс, URL и передачу файла больше одного recv.
    address, _, _ = server_factory()
    with socket.create_connection(address, timeout=2) as client:
        client.sendall(request("GET", target))
        status, headers, body = split_response(read_response(client))
    assert status == "HTTP/1.1 200 OK"
    assert body == expected
    assert int(headers["Content-Length"]) == len(expected)


@pytest.mark.parametrize("stage", ["accept", "settimeout", "submit"])
def test_server_rolls_back_slot_before_submission(root, monkeypatch, stage):
    # Воспроизводим ошибки до передачи задачи без открытия настоящего порта.
    slots = BoundedSemaphore(1)
    listener, connection, executor = Mock(), Mock(), Mock()
    listener.accept.return_value = (connection, ("127.0.0.1", 1))
    if stage == "accept":
        listener.accept.side_effect = OSError("test accept failure")
    elif stage == "settimeout":
        connection.settimeout.side_effect = OSError("test socket failure")
    else:
        executor.submit.side_effect = RuntimeError("test submission failure")
    monkeypatch.setattr(httpd, "BoundedSemaphore", lambda value: slots)
    monkeypatch.setattr(
        httpd, "ThreadPoolExecutor", lambda **kwargs: nullcontext(executor)
    )

    with pytest.raises((OSError, RuntimeError), match="test"):
        stop = httpd.multiprocessing.get_context("spawn").Event()
        httpd.server_worker(listener, root, 1, 0, stop)

    # Ошибка не должна терять разрешение или оставлять уже принятый сокет
    # открытым.
    assert slots.acquire(blocking=False)
    assert not slots.acquire(blocking=False)
    if stage != "accept":
        connection.close.assert_called_once()


def test_worker_releases_slot_on_unexpected_exception(root, monkeypatch):
    # finally возвращает место даже для ошибки, которую wrapper не
    # перехватывает.
    slots = BoundedSemaphore(1)
    slots.acquire()
    monkeypatch.setattr(
        httpd, "handle_request", Mock(side_effect=RuntimeError("unexpected"))
    )
    with pytest.raises(RuntimeError, match="unexpected"):
        httpd.handle_client(Mock(), ("127.0.0.1", 1), root, slots)
    assert slots.acquire(blocking=False)
    assert not slots.acquire(blocking=False)


@pytest.mark.parametrize("index_link", [False, True])
def test_resolve_path_rejects_simulated_external_link(
    root, index_link, monkeypatch
):
    # Имитируем результат разрешения ссылки без специальных прав Windows.
    # Это проверка границы root; настоящую работу ссылок файловой системы не
    # проверяем.
    link = root / "guide" / "index.html" if index_link else root / "link.html"
    outside = root.parent / "secret.txt"
    original_resolve = Path.resolve

    def resolve(path, *args, **kwargs):
        if path == link:
            return outside
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(ValueError):
        httpd.resolve_path("/guide/" if index_link else "/link.html", root)


def test_live_server_releases_slot_after_client_timeout(server_factory):
    # Пять секунд молчания должны освободить единственное место для следующего
    # клиента.
    address, _, _ = server_factory(threads=1, max_queue=0)
    with socket.create_connection(address, timeout=7) as slow:
        slow.sendall(b"GET / HTTP/1.1\r\n")
        assert slow.recv(1) == b""
    with socket.create_connection(address, timeout=2) as client:
        client.sendall(request("GET", "/"))
        assert split_response(read_response(client))[2] == b"home"


def test_live_server_small_concurrent_series(server_factory):
    # Небольшая проверка стабильности, не замена нагрузочного тестирования
    # ab/wrk.
    address, _, _ = server_factory(threads=4, max_queue=8)

    def fetch(_):
        with socket.create_connection(address, timeout=5) as client:
            client.sendall(request("GET", "/"))
            status, headers, body = split_response(read_response(client))
            assert status == "HTTP/1.1 200 OK"
            assert headers["Content-Length"] == "4"
            return body

    with ThreadPoolExecutor(max_workers=8) as clients:
        assert list(clients.map(fetch, range(100))) == [b"home"] * 100


def test_worker_skips_accept_when_stop_is_already_set(root):
    # Поднятый заранее флаг не позволяет начать приём соединений.
    stop = httpd.multiprocessing.get_context("spawn").Event()
    stop.set()
    listener = Mock()

    httpd.server_worker(listener, root, 1, 0, stop)

    listener.accept.assert_not_called()
    # Слушающим сокетом пока владеет вызывающая функция.
    listener.close.assert_not_called()


def test_worker_stops_after_accept_timeout_and_returns_slot(root, monkeypatch):
    # Таймаут возвращает управление к проверке флага и освобождает место.
    stop = httpd.multiprocessing.get_context("spawn").Event()
    slots = BoundedSemaphore(1)
    listener = Mock()

    def timeout():
        stop.set()
        raise TimeoutError

    listener.accept.side_effect = timeout
    monkeypatch.setattr(httpd, "BoundedSemaphore", lambda value: slots)

    httpd.server_worker(listener, root, 1, 0, stop)

    listener.accept.assert_called_once()
    assert slots.acquire(blocking=False)
    assert not slots.acquire(blocking=False)
    listener.close.assert_not_called()


def test_worker_finishes_accepted_request_before_stopping(root):
    # Флаг не обрывает принятое соединение: пул завершает передачу ответа.
    stop = httpd.multiprocessing.get_context("spawn").Event()
    listener = Mock()
    client, connection = socket.socketpair()
    with client, connection:
        client.settimeout(2)
        client.sendall(request("GET", "/"))

        def accept():
            stop.set()
            return connection, ("127.0.0.1", 12345)

        listener.accept.side_effect = accept
        httpd.server_worker(listener, root, 1, 0, stop)
        status, _, body = split_response(read_response(client))

    assert status == "HTTP/1.1 200 OK"
    assert body == b"home"
    listener.accept.assert_called_once()


@pytest.mark.parametrize("fails", [False, True])
def test_worker_entry_configures_process_and_closes_socket(
    root, monkeypatch, fails
):
    # Подменяем signal.signal, чтобы не отключить Ctrl+C у самого pytest.
    configure_signal = Mock()
    monkeypatch.setattr(httpd.signal, "signal", configure_signal)
    listener = socket.socket()
    stop = Mock()

    def run(server, document_root, threads, max_queue, stop_event):
        # Дочерний процесс явно настраивает таймаут перед приёмом запросов.
        assert server.gettimeout() == 0.5
        assert server.fileno() != -1
        if fails:
            raise RuntimeError("worker failed")

    worker = Mock(side_effect=run)
    monkeypatch.setattr(httpd, "server_worker", worker)
    expectation = (
        pytest.raises(RuntimeError, match="worker failed")
        if fails
        else nullcontext()
    )
    try:
        with expectation:
            httpd.worker_entry(listener, root, 2, 3, stop)
        worker.assert_called_once_with(listener, root, 2, 3, stop)
        configure_signal.assert_called_once_with(
            httpd.signal.SIGINT, httpd.signal.SIG_IGN
        )
        # Экземпляр сокета закрывается и при успехе, и при ошибке worker.
        assert listener.fileno() == -1
    finally:
        listener.close()


@pytest.fixture
def supervisor(monkeypatch):
    # Подменяем процессы: проверяем управление без настоящих дочерних PID.
    ctx, stop, child, listener = Mock(), Mock(), Mock(), Mock()
    ctx.Event.return_value = stop
    ctx.Process.return_value = child
    stop.wait.return_value = True
    child.is_alive.return_value = False
    monkeypatch.setattr(httpd.multiprocessing, "get_context", lambda _: ctx)
    monkeypatch.setattr(
        httpd.socket, "create_server", lambda address: nullcontext(listener)
    )
    local_worker = Mock()
    monkeypatch.setattr(httpd, "server_worker", local_worker)
    return ctx, stop, child, listener, local_worker


def test_supervisor_starts_workers_and_signals_before_join(root, supervisor):
    # Родитель сначала просит детей остановиться и только затем ждёт их.
    ctx, stop, child, listener, local_worker = supervisor

    def join(timeout):
        stop.set.assert_called_once()
        assert timeout == 10

    child.join.side_effect = join
    httpd.serve("127.0.0.1", 8080, root, workers=1)

    ctx.Process.assert_called_once_with(
        target=httpd.worker_entry,
        args=(listener, root, 4, 8, stop),
    )
    child.start.assert_called_once()
    child.join.assert_called_once_with(timeout=10)
    child.terminate.assert_not_called()
    # Обслуживание соединений не должно запускаться в родителе.
    local_worker.assert_not_called()


def test_supervisor_cleans_started_workers_if_next_start_fails(
    root, supervisor
):
    # Ошибка запуска второго ребёнка не оставляет первого без остановки.
    ctx, stop, first, _, _ = supervisor
    second = Mock()
    second.start.side_effect = RuntimeError("start failed")
    ctx.Process.side_effect = [first, second]

    with pytest.raises(RuntimeError, match="start failed"):
        httpd.serve("127.0.0.1", 8080, root, workers=2)

    stop.set.assert_called_once()
    first.join.assert_called_once_with(timeout=10)
    second.join.assert_not_called()


def test_supervisor_detects_exited_worker(root, supervisor):
    # Неожиданно умерший worker вызывает ошибку и общую остановку.
    _, stop, child, _, _ = supervisor
    stop.wait.return_value = False

    with pytest.raises(RuntimeError, match="неожиданно завершился"):
        httpd.serve("127.0.0.1", 8080, root)

    stop.set.assert_called_once()
    child.join.assert_called_once_with(timeout=10)


def test_supervisor_terminates_worker_after_grace_timeout(root, supervisor):
    # Истечение join(timeout=10) само по себе не останавливает процесс.
    _, stop, child, _, _ = supervisor
    child.is_alive.return_value = True

    httpd.serve("127.0.0.1", 8080, root)

    stop.set.assert_called_once()
    child.terminate.assert_called_once()
    assert child.join.call_count == 2
    child.join.assert_called_with()


def test_supervisor_signals_workers_on_keyboard_interrupt(root, supervisor):
    # Ctrl+C проходит через finally: дети получают флаг перед join.
    _, stop, child, _, _ = supervisor
    stop.wait.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        httpd.serve("127.0.0.1", 8080, root)

    stop.set.assert_called_once()
    child.join.assert_called_once_with(timeout=10)


def test_live_two_process_workers_share_listener(server_factory):
    # При одном слоте на процесс два медленных клиента занимают обоих.
    address, parent, log = server_factory(workers=2, threads=1, max_queue=0)
    with ExitStack() as stack:
        slow = []
        for _ in range(2):
            client = stack.enter_context(
                socket.create_connection(address, timeout=3)
            )
            client.sendall(b"GET / HTTP/1.1\r\n")
            wait_until(lambda: accepted(log, client), parent, log)
            slow.append(client)

        fast = stack.enter_context(
            socket.create_connection(address, timeout=3)
        )
        fast.sendall(request("GET", "/"))
        fast.settimeout(0.2)
        with pytest.raises(TimeoutError):
            fast.recv(1)
        assert not accepted(log, fast)

        # Освобождаем один процесс; второй всё ещё занят своим клиентом.
        slow[0].shutdown(socket.SHUT_WR)
        fast.settimeout(3)
        assert split_response(read_response(fast))[2] == b"home"
        slow[1].sendall(b"\r\n")
        assert split_response(read_response(slow[1]))[2] == b"home"


def test_spawned_workers_exit_cleanly_after_shared_event(root):
    # Настоящий spawn передаёт слушающий сокет и общий Event двум детям.
    ctx = httpd.multiprocessing.get_context("spawn")
    stop = ctx.Event()
    processes = []
    with socket.create_server(("127.0.0.1", 0)) as listener:
        address = listener.getsockname()
        try:
            for _ in range(2):
                child = ctx.Process(
                    target=httpd.worker_entry,
                    args=(listener, root, 1, 0, stop),
                )
                child.start()
                processes.append(child)

            with socket.create_connection(address, timeout=5) as client:
                client.sendall(request("GET", "/"))
                assert split_response(read_response(client))[2] == b"home"

            stop.set()
            for child in processes:
                child.join(timeout=5)
                assert not child.is_alive()
                assert child.exitcode == 0
        finally:
            # Даже при провале проверки завершаем только созданных детей.
            stop.set()
            for child in processes:
                child.join(timeout=2)
                if child.is_alive():
                    child.terminate()
                    child.join(timeout=5)
                child.close()

    # Все экземпляры listener закрыты: тот же адрес снова можно занять.
    with socket.create_server(address):
        pass
