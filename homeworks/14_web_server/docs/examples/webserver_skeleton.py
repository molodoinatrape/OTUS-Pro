import socket
import threading
import os

# Конфигурация сервера
HOST = 'localhost'
PORT = 8080
DOCUMENT_ROOT = './www'  # Корневая папка для статических файлов

# Функция для обработки клиентских запросов
def handle_request(client_socket):
    try:
        request = client_socket.recv(1024).decode('utf-8')
        if not request:
            return

        headers = request.split('\n')
        method, path, _ = headers[0].split()

        if method not in ['GET', 'HEAD']:
            response = 'HTTP/1.1 405 Method Not Allowed\n\nMethod Not Allowed'
            client_socket.sendall(response.encode('utf-8'))
            return

        # Удаление начального символа '/'
        if path == '/':
            path = '/index.html'
        
        file_path = DOCUMENT_ROOT + path

        if os.path.isfile(file_path):
            with open(file_path, 'rb') as file:
                body = file.read()
            response_headers = 'HTTP/1.1 200 OK\n'
            response_headers += f'Content-Length: {len(body)}\n'
            response_headers += 'Content-Type: text/html\n\n'
            response = response_headers.encode('utf-8')

            if method == 'GET':
                response += body
        else:
            response = 'HTTP/1.1 404 Not Found\n\n404 Not Found'.encode('utf-8')

        client_socket.sendall(response)
    finally:
        client_socket.close()

# Функция для запуска сервера
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f'Server started on {HOST}:{PORT}')

    try:
        while True:
            client_socket, _ = server_socket.accept()
            client_handler = threading.Thread(
                target=handle_request,
                args=(client_socket,)
            )
            client_handler.start()
    finally:
        server_socket.close()

if __name__ == '__main__':
    start_server()