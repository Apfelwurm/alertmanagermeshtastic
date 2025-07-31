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
from .signals import (
    message_received,
    queue_size_updated,
    meshtastic_connected,
    clear_queue_issued,
)
from .util import start_thread


logger = logging.getLogger(__name__)


def create_app(clearsecret, api_tokens=None) -> Application:
    if api_tokens is None:
        api_tokens = set()
    return Application(clearsecret=clearsecret, api_tokens=api_tokens)


class Application:
    def __init__(self, clearsecret, api_tokens=None) -> None:
        if api_tokens is None:
            api_tokens = set()
        self._url_map = Map(
            [
                Rule('/alert', endpoint='alert', methods=['POST']),
                Rule('/metrics', endpoint='metrics', methods=['GET']),
                Rule('/clear_queue', endpoint='clearqueue', methods=['GET']),
            ]
        )
        self.queue_size = 0  # Initialize queue size
        self.clearsecret = clearsecret
        self.api_tokens = api_tokens
        self.meshtastic_connected = False
        self.connect_to_signals()
        # Signals are allowed be sent from here on.

    def connect_to_signals(self) -> None:
        queue_size_updated.connect(self.update_queue_size)
        meshtastic_connected.connect(self.update_meshtastic_connected)

    def update_meshtastic_connected(
        self, meshtastic_connected: bool
    ) -> None:  # Define a new method
        self.meshtastic_connected = meshtastic_connected

    def update_queue_size(self, queue_size: int) -> None:  # Define a new method
        self.queue_size = queue_size

    def _check_authentication(self, request: Request) -> Response:
        """Check API token authentication. Returns Response if authentication fails, None if success."""
        authorization = request.headers.get('Authorization')
        
        if not authorization:
            return Response('Unauthorized', status=HTTPStatus.UNAUTHORIZED)
        
        # Expected format: "Token <token>"
        parts = authorization.split(' ', 1)
        if len(parts) != 2 or parts[0] != 'Token':
            return Response('Unauthorized', status=HTTPStatus.UNAUTHORIZED)
        
        token = parts[1]
        if token not in self.api_tokens:
            return Response('Forbidden', status=HTTPStatus.FORBIDDEN)
        
        return None  # Authentication successful

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
            
            # Check API token authentication for /alert endpoint
            if endpoint == 'alert' and self.api_tokens:
                auth_result = self._check_authentication(request)
                if auth_result:
                    return auth_result
            
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

    def on_clearqueue(self, request):
        try:
            secret = request.args.get('secret')
            if secret != self.clearsecret:
                return Response('Forbidden', status=HTTPStatus.FORBIDDEN)

            clear_queue_issued.send()

            return Response('Queue cleared', status=HTTPStatus.OK)
        except Exception as error:
            logger.error("\t could clear alert queue: %s ", error)
            return Response(
                'clearing queue faild', status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

    def on_metrics(self, request: Request) -> Response:
        response = '# HELP message_queue_size The size of the message queue.\n'
        response += '# TYPE message_queue_size gauge\n'
        response += f'message_queue_size {self.queue_size}\n'
        response += '# HELP meshtastic_connected shows if meshtastic is connected or not.\n'
        response += '# TYPE meshtastic_connected gauge\n'
        response += f'meshtastic_connected {int(self.meshtastic_connected)}'
        return Response(response, status=HTTPStatus.OK)


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
    app = create_app(config.clearsecret, config.api_tokens)

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
