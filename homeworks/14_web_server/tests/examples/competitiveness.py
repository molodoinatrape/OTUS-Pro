import socket


def receive_response(sock):
    response = b""
    while True:
        chunk = sock.recv(4096)
        if chunk == b"":
            return response
        response += chunk


address = ("127.0.0.1", 8080)

with socket.create_connection(address, timeout=2) as slow:
    # Нет конечной пустой строки: сервер пока не может обработать запрос.
    slow.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n")

    with socket.create_connection(address, timeout=2) as fast:
        # Второй клиент сразу отправляет полный запрос.
        fast.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
        response = receive_response(fast)
        assert response.startswith(b"HTTP/1.1 200 OK\r\n")
        print("Второй клиент получил 200, первый ещё не завершил запрос")

    # Только теперь разрешаем обработать запрос первого клиента.
    slow.sendall(b"\r\n")
    response = receive_response(slow)
    assert response.startswith(b"HTTP/1.1 200 OK\r\n")
    print("Первый клиент тоже получил 200")
