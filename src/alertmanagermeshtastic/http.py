"""
alertmanagermeshtastic.http
~~~~~~~~~~~~~~~~

HTTP server to receive messages

:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

from __future__ import annotations
from http import HTTPStatus
import logging
import sys
from typing import Optional
from wsgiref.simple_server import make_server, ServerHandler, WSGIServer

from werkzeug.datastructures import Headers
from werkzeug.exceptions import abort, HTTPException
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response

from .config import HttpConfig
from .signals import message_received
from .util import start_thread


logger = logging.getLogger(__name__)


def create_app(
    api_tokens: set[str], channel_tokens_to_channel_names: dict[str, str]
) -> Application:
    return Application(api_tokens, channel_tokens_to_channel_names)


class Application:
    def __init__(
        self,
        api_tokens: set[str],
        channel_tokens_to_channel_names: dict[str, str],
    ) -> None:
        self._api_tokens = api_tokens
        self._channel_tokens_to_channel_names = channel_tokens_to_channel_names

        self._url_map = Map(
            [
                Rule('/', endpoint='root'),
                Rule('/ct/<channel_token>', endpoint='channel_token'),
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

    def on_root(self, request: Request) -> Response:
        if self._api_tokens:
            api_token = _get_api_token(request.headers)
            if not api_token:
                abort(HTTPStatus.UNAUTHORIZED)

            if api_token not in self._api_tokens:
                abort(HTTPStatus.FORBIDDEN)

        data = _extract_payload(request, {'channel', 'text'})

        message_received.send(
            channel_name=data['channel'],
            text=data['text'],
            source_ip_address=request.remote_addr,
        )

        return Response('', status=HTTPStatus.ACCEPTED)

    def on_channel_token(
        self, request: Request, channel_token: str
    ) -> Response:
        channel_name = self._channel_tokens_to_channel_names.get(channel_token)
        if channel_name is None:
            abort(HTTPStatus.NOT_FOUND)

        data = _extract_payload(request, {'text'})

        message_received.send(
            channel_name=channel_name,
            text=data['text'],
            source_ip_address=request.remote_addr,
        )

        return Response('', status=HTTPStatus.ACCEPTED)


def _get_api_token(headers: Headers) -> Optional[str]:
    authorization_value = headers.get('Authorization')
    if not authorization_value:
        return None

    prefix = 'Token '
    if not authorization_value.startswith(prefix):
        return None

    return authorization_value[len(prefix) :]


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
    app = create_app(config.api_tokens, config.channel_tokens_to_channel_names)

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
