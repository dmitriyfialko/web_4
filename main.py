from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse as ur
from pathlib import Path
from mimetypes import guess_type
import socket
import logging
from threading import Thread
from datetime import datetime
import json


SERVER_S = ('127.0.0.1', 5000)


class HTTPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        self.send_to_socket_server(body)

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def do_GET(self):
        route = ur.urlparse(self.path)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('message.html')
            case _:
                f = Path(f'./front-init{route.path}')
                if f.exists():
                    self.send_static(route.path)
                else:
                    self.send_html('error.html', status_code=404)

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(f'front-init/{filename}', 'rb') as f:
            self.wfile.write(f.read())

    def send_static(self, filename):
        self.send_response(200)
        if mime_type := guess_type(filename):
            self.send_header('Content-Type', mime_type[1])
        else:
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        with open(f'front-init/{filename}', 'rb') as f:
            self.wfile.write(f.read())

    def send_to_socket_server(self, body):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(body, SERVER_S)


def run_http_server(server=HTTPServer, handler=HTTPHandler):
    address = ('', 3000)
    http_server = server(address, handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def save_data(data):
    data = ur.unquote_plus(data.decode())
    data = data.lstrip('username=').split('&message=')
    tm = datetime.now()
    message = {
        datetime.strftime(tm, '%Y-%m-%d %H-%M-%S'): {
            'username': data[0],
            'message': data[1]
        }
    }
    data_json = '{}'
    try:
        with open('storage/data.json', 'r', encoding='UTF-8') as f:
            data_json = f.read()
    except FileNotFoundError:
        logging.info('File data.json will be created')
    except Exception as err:
        logging.error(f'Failed to save data\n{err}')
    data_json = json.loads(data_json)
    data_json.update(message)
    try:
        with open('storage/data.json', 'w', encoding='UTF-8') as f:
            f.write(json.dumps(data_json, ensure_ascii=False, indent=4))
    except Exception as err:
        logging.error(f'Failed to save data\n{err}')


def run_socket_server(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((ip, port))
    try:
        while True:
            data, address = server_socket.recvfrom(2048)
            save_data(data)
    except KeyboardInterrupt:
        logging.info('Socket server stopped')
    finally:
        server_socket.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(threadName)s %(message)s')

    thread_http = Thread(target=run_http_server)
    thread_http.start()

    thread_socket = Thread(target=run_socket_server, args=SERVER_S)
    thread_socket.start()


