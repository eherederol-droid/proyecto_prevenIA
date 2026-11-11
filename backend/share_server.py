"""Serve the frontend and proxy only the API and uploaded media for a demo tunnel."""
from http.client import HTTPConnection
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import unquote, urlsplit


BACKEND_HOST = '127.0.0.1'
BACKEND_PORT = 8000
FRONTEND_ROOT = Path(__file__).resolve().parent.parent / 'frontend'
PUBLIC_ASSETS = {
    '/logo_prevenIA.png': Path(__file__).resolve().parent.parent / 'logo_prevenIA.png',
}
MEDIA_ROOT = (Path(__file__).resolve().parent / 'media').resolve()
MAX_REQUEST_BYTES = 20 * 1024 * 1024
PROXY_PREFIXES = ('/api/', '/static/')
HOP_BY_HOP_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade',
}


class ShareHandler(SimpleHTTPRequestHandler):
    server_version = 'PrevenIA-Demo'
    sys_version = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_ROOT), **kwargs)

    def do_GET(self):
        self._handle_request()

    def do_HEAD(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def do_PUT(self):
        self._handle_request()

    def do_PATCH(self):
        self._handle_request()

    def do_DELETE(self):
        self._handle_request()

    def do_OPTIONS(self):
        self._handle_request()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def _handle_request(self):
        path = urlsplit(self.path).path
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/login.html')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return

        if path == '/healthz':
            body = b'PrevenIA demo server is ready.'
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)
            return

        if path in PUBLIC_ASSETS:
            self._serve_file(PUBLIC_ASSETS[path])
            return

        if path.startswith('/media/'):
            self._serve_media(path)
            return

        if path.startswith(PROXY_PREFIXES):
            self._proxy_request()
            return

        if path.startswith('/admin'):
            self.send_error(404)
            return

        if self.command in ('GET', 'HEAD'):
            if self.command == 'HEAD':
                super().do_HEAD()
            else:
                super().do_GET()
            return

        self.send_error(404)

    def _serve_file(self, target):
        if not target.is_file():
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', guess_type(target.name)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(target.stat().st_size))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if self.command != 'HEAD':
            with target.open('rb') as asset_file:
                self.copyfile(asset_file, self.wfile)

    def _serve_media(self, path):
        relative_path = unquote(path[len('/media/'):])
        target = (MEDIA_ROOT / relative_path).resolve()
        if not target.is_relative_to(MEDIA_ROOT) or not target.is_file():
            self.send_error(404)
            return

        content_type = guess_type(target.name)[0] or 'application/octet-stream'
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(target.stat().st_size))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if self.command != 'HEAD':
            with target.open('rb') as media_file:
                self.copyfile(media_file, self.wfile)

    def _proxy_request(self):
        try:
            content_length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            self.send_error(400, 'Invalid Content-Length')
            return
        if content_length < 0 or content_length > MAX_REQUEST_BYTES:
            self.send_error(413, 'Request body too large')
            return

        body = self.rfile.read(content_length) if content_length else None
        request_headers = {
            name: value
            for name, value in self.headers.items()
            if name.lower() not in HOP_BY_HOP_HEADERS
            and name.lower() not in {
                'host',
                'content-length',
                'x-forwarded-for',
                'x-forwarded-host',
                'x-forwarded-proto',
            }
        }
        request_headers['Host'] = f'{BACKEND_HOST}:{BACKEND_PORT}'
        request_headers['X-Forwarded-For'] = self.client_address[0]
        request_headers['X-Forwarded-Proto'] = 'https'
        if body is not None:
            request_headers['Content-Length'] = str(len(body))

        request_target = self.path
        connection = HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=120)
        try:
            connection.request(
                self.command,
                request_target,
                body=body,
                headers=request_headers,
            )
            response = connection.getresponse()
            response_body = response.read()
            response_headers = response.getheaders()
            self.send_response(response.status, response.reason)
            for name, value in response_headers:
                if name.lower() not in HOP_BY_HOP_HEADERS and name.lower() != 'content-length':
                    self.send_header(name, value)
            self.send_header('Content-Length', str(len(response_body)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(response_body)
        except OSError:
            self.send_error(502, 'The local API server is unavailable')
        finally:
            connection.close()

    def log_message(self, format_string, *args):
        path = urlsplit(self.path).path
        print(f'{self.client_address[0]} {self.command} {path}', flush=True)


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 3001), ShareHandler)
    print('PrevenIA demo proxy listening on 127.0.0.1:3001', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
