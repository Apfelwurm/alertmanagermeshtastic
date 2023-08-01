"""
alertmanagermeshtastic.http
~~~~~~~~~~~~~~~~

HTTP server to receive messages

:Copyright: 2007-2022 Jochen Kupperschmidt
:Copyright: 2023 Alexander Volz
:License: MIT, see LICENSE for details.
"""

from __future__ import annotations
from http import HTTPStatus
import logging
import sys
from wsgiref.simple_server import make_server, ServerHandler, WSGIServer

from werkzeug.exceptions import abort, HTTPException
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response

from .config import HttpConfig
from .signals import message_received
from .util import start_thread


logger = logging.getLogger(__name__)


def create_app() -> Application:
    return Application()


class Application:
    def __init__(
        self,
    ) -> None:
        self._url_map = Map(
            [
                Rule('/alert', endpoint='alert', methods=['POST']),
            ]
        )

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def dispatch_request(self, request: Request):
        adapter = self._url_map.bind_to_environ(request.environ)

        try:
            endpoint, values = adapter.match()
            handler = getattr(self, f'on_{endpoint}')
            return handler(request, **values)
        except HTTPException as exc:
            return exc

    def on_alert(self, request: Request) -> Response:
        try:
            data = _extract_payload(request, {'alerts'})

            for alert in data["alerts"]:
                logger.debug("\t [%s] received", alert["fingerprint"])
                message_received.send(alert=alert)
            return Response('Alert OK', status=HTTPStatus.OK)
        except Exception as error:
            logger.error("\t could not queue alerts: %s ", error)
            return Response('Alert fail', status=HTTPStatus.OK)


def _extract_payload(request: Request, keys: set[str]) -> dict[str, str]:
    """Extract values for given keys from JSON payload."""
    if not request.is_json:
        abort(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    payload = request.json
    if payload is None:
        abort(HTTPStatus.BAD_REQUEST)

    data = {}
    try:
        for key in keys:
            data[key] = payload[key]
    except KeyError:
        abort(HTTPStatus.BAD_REQUEST)

    return data


# Override value of `Server:` header sent by wsgiref.
ServerHandler.server_software = 'alertmanagermeshtastic'


def create_server(config: HttpConfig) -> WSGIServer:
    """Create the HTTP server."""
    app = create_app()

    return make_server(config.host, config.port, app)


def start_receive_server(config: HttpConfig) -> None:
    """Start in a separate thread."""
    try:
        server = create_server(config)
    except OSError as e:
        sys.stderr.write(f'Error {e.errno:d}: {e.strerror}\n')
        sys.stderr.write(
            f'Probably no permission to open port {config.port}. '
            'Try to specify a port number above 1,024 (or even '
            '4,096) and up to 65,535.\n'
        )
        sys.exit(1)

    thread_name = server.__class__.__name__
    start_thread(server.serve_forever, thread_name)
    logger.info('Listening for HTTP requests on %s:%d.', *server.server_address)
