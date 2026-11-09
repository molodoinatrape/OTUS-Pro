import os
import time
import socket
import signal
import argparse
import multiprocessing
from threading import BoundedSemaphore
from email.utils import formatdate
from pathlib import Path
from urllib.parse import urlsplit, unquote
from concurrent.futures import ThreadPoolExecutor


def receive_headers(
        client_socket,
        max_header_size: int = 65536,
        header_timeout: float = 5.0,
) -> bytes:
    """
    Чтение заголовков
    """
    headers = b''
    original_timeout = client_socket.gettimeout()
    deadline = time.monotonic() + header_timeout

    try:
        while b'\r\n\r\n' not in headers:
            if len(headers) >= max_header_size:
                raise ValueError('Превышен лимит размера заголовков')

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Истекло время получения заголовков')

            if original_timeout is None:
                client_socket.settimeout(remaining)
            else:
                client_socket.settimeout(min(original_timeout, remaining))

            chunk = client_socket.recv(
                min(4096, max_header_size - len(headers))
            )
            if chunk == b'':
                raise ValueError(
                    'Соединение завершено до получения полных заголовков'
                )
            headers += chunk

        separator = headers.find(b'\r\n\r\n')
        headers = headers[:separator+4]
    finally:
        client_socket.settimeout(original_timeout)

    return headers


def parse_request_line(headers: bytes) -> tuple[str, str, str]:
    """
    Разбор запроса на method, url, version
    """
    request_line = headers.split(b'\r\n', 1)[0]
    request_line = request_line.decode('ascii')

    if len(request_line.split()) != 3:
        raise ValueError(f'{request_line} - ошибочная строка')

    method, url, version = request_line.split()

    return method, url, version


def resolve_path(target: str, document_root: Path) -> Path:
    """
    Поиск пути файла
    """
    root = document_root.resolve()
    url_path = (
        unquote(
            urlsplit(target).path
        )
    ).lstrip('/')

    directory_requested = url_path.endswith('/')

    path = root / url_path
    resolved_path = path.resolve()

    resolved_path.relative_to(root)

    if directory_requested and not resolved_path.is_dir():
        raise NotADirectoryError('Не является каталогом')

    if resolved_path.is_dir():
        resolved_path = (resolved_path / 'index.html').resolve()
        resolved_path.relative_to(root)

        if not resolved_path.exists():
            raise FileNotFoundError('Индекс каталога отсутствует')

    return resolved_path


def get_content_type(file_path: Path) -> str:
    extensions = {
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.swf': 'application/x-shockwave-flash',
    }

    extension = file_path.suffix.lower()
    content_type = extensions.get(extension, 'application/octet-stream')

    return content_type


def build_response(
        status_code: int,
        body: bytes,
        content_type: str,
        head_only: bool = False,
        content_length: int | None = None,
) -> bytes:
    """
    Сборка ответа
    """
    status_codes = {
        200: 'OK',
        403: 'Forbidden',
        404: 'Not Found',
        405: 'Method Not Allowed',
    }

    if content_length is None:
        content_length = len(body)

    headers = [
        f'HTTP/1.1 {status_code} {status_codes[status_code]}',
        f'Date: {formatdate(usegmt=True)}',
        'Server: StudyServer',
        f'Content-Type: {content_type}',
        f'Content-Length: {content_length}',
        'Connection: close',
    ]
    if status_code == 405:
        headers.append('Allow: GET, HEAD')

    response = '\r\n'.join(headers) + '\r\n\r\n'
    response = response.encode('ascii')

    if not head_only:
        response += body

    return response


def handle_request(client_socket, document_root: Path) -> None:
    """
    Обработчик одного соединения
    """
    with client_socket:
        headers = receive_headers(client_socket)
        method, url, version = parse_request_line(headers)

        head_only = (method == 'HEAD')

        if method not in ('HEAD', 'GET'):
            client_socket.sendall(build_response(
                status_code=405,
                body=b'Unknown method',
                content_type='text/plain',
                head_only=head_only,
            ))
            return None

        try:
            path = resolve_path(url, document_root)
            file = path.open('rb')
        except (ValueError, PermissionError, IsADirectoryError):
            response = build_response(
                status_code=403,
                body=b'Forbidden',
                content_type='text/plain',
                head_only=head_only,
            )
        except (FileNotFoundError, NotADirectoryError):
            response = build_response(
                status_code=404,
                body=b'Not Found',
                content_type='text/plain',
                head_only=head_only,
            )
        else:
            with file:
                content_length = os.fstat(file.fileno()).st_size
                response = build_response(
                    status_code=200,
                    body=b'',
                    content_type=get_content_type(path),
                    head_only=head_only,
                    content_length=content_length,
                )

                client_socket.sendall(response)

                if not head_only:
                    remaining = content_length

                    while remaining > 0:
                        chunk = file.read(min(65536, remaining))

                        if chunk == b'':
                            raise OSError(
                                'Файл закончился раньше объявленного размера'
                            )
                        client_socket.sendall(chunk)
                        remaining -= len(chunk)

                return None

        client_socket.sendall(response)

        return None


def handle_client(
        client_socket,
        client_address,
        document_root: Path,
        slots,
) -> None:
    try:
        handle_request(client_socket, document_root)
    except (ValueError, OSError) as error:
        print(f'Ошибка соединения с {client_address}: {error}')
    finally:
        slots.release()


def server_worker(
        server,
        document_root: Path,
        threads: int,
        max_queue: int,
        stop_event,
) -> None:
    """
    Приём соединений и обслуживание через пул потоков
    """
    with ThreadPoolExecutor(max_workers=threads) as executor:
        slots = BoundedSemaphore(threads + max_queue)

        while not stop_event.is_set():
            if not slots.acquire(timeout=0.5):
                continue

            client_socket = None
            submitted = False

            try:
                try:
                    client_socket, client_address = server.accept()
                except TimeoutError:
                    continue

                print(f'Принято соединение: {client_address}')
                client_socket.settimeout(5)

                executor.submit(
                    handle_client,
                    client_socket,
                    client_address,
                    document_root,
                    slots
                )
                submitted = True
            finally:
                if not submitted:
                    try:
                        if client_socket is not None:
                            client_socket.close()
                    finally:
                        slots.release()


def worker_entry(
        server,
        document_root: Path,
        threads: int,
        max_queue: int,
        stop_event,
) -> None:
    """
    Запуск и завершение дочернего рабочего процесса
    """
    # Ctrl+C обрабатывает родитель и поднимает общий stop_event
    # Этот процесс завершается по флагу, а не через KeyboardInterrupt
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    with server:
        server.settimeout(0.5)

        server_worker(
            server,
            document_root,
            threads,
            max_queue,
            stop_event,
        )


def serve(
        host: str,
        port: int,
        document_root: Path,
        threads: int = 4,
        max_queue: int = 8,
        workers: int = 1,
) -> None:
    """
    Создание и закрытие слушающего сокета
    """
    ctx = multiprocessing.get_context('spawn')
    stop_event = ctx.Event()

    with socket.create_server((host, port)) as server:
        print(f'Сервер запущен: http://{host}:{port}\r\n'
              f'Рабочих процессов: {workers}\r\n'
              f'Потоков на процесс: {threads}\r\n'
              f'Лимит задач на процесс: {threads + max_queue}'
              )

        # Ограничиваем ожидание accept в рабочих процессах,
        # чтобы они регулярно проверяли общий флаг остановки.
        server.settimeout(0.5)

        processes = []

        try:
            for worker in range(workers):
                process = ctx.Process(
                    target=worker_entry,
                    args=(
                        server,
                        document_root,
                        threads,
                        max_queue,
                        stop_event
                    ),
                )
                process.start()
                processes.append(process)

            while not stop_event.wait(0.5):
                for process in processes:
                    if not process.is_alive():
                        raise RuntimeError(
                            f'Рабочий процесс {process.pid} '
                            f'неожиданно завершился'
                        )
        finally:
            stop_event.set()

            for process in processes:
                process.join(timeout=10)
                if process.is_alive():
                    process.terminate()
                    process.join()


def parse_args(argv=None) -> argparse.Namespace:
    """
    Параметры при запуске из терминала
    """
    parser = argparse.ArgumentParser(
        description='HTTP-сервер статических файлов'
    )
    parser.add_argument(
        '-r',
        dest='document_root',
        required=True,
        type=Path,
        help='Корневая папка публикуемых файлов'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
    )
    parser.add_argument(
        '--threads',
        type=int,
        default=4,
        help='Количество рабочих потоков'
    )
    parser.add_argument(
        '--max-queue',
        type=int,
        default=8,
    )
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=1,
        help='Количество рабочих процессов'
    )

    args = parser.parse_args(argv)

    if args.port < 1 or args.port > 65535:
        parser.error('Порт должен находиться в диапазоне от 1 до 65535')

    args.document_root = args.document_root.resolve()
    if not args.document_root.is_dir():
        parser.error('Несуществующий каталог')

    if args.threads < 1:
        parser.error('Потоков не может быть < 1')

    if args.max_queue < 0:
        parser.error('Очередь запросов не может быть < 0')

    if args.workers < 1:
        parser.error('Рабочих процессов должно быть не < 1')

    return args


if __name__ == '__main__':
    args = parse_args()
    try:
        serve(
            args.host,
            args.port,
            args.document_root,
            threads=args.threads,
            max_queue=args.max_queue,
            workers=args.workers,
        )
    except KeyboardInterrupt:
        print('\nСервер остановлен')
