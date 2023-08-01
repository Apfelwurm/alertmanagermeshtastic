"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


@pytest.fixture
def server(make_server):
    return make_server()


@pytest.fixture
def restricted_server(make_server):
    api_tokens = {
        'gAT3KHqpb94YQ7IMhR-qMH5tRquwLnHoyik_lZItTQY',
        'qeV4Jf_PYxAySktCODORTKSH1gs117qJXwoqg5YoDBU',
    }
    return make_server(api_tokens=api_tokens)


# unrestricted access


def test_receive_server_with_valid_request(server):
    data = {
        'channel': '#party',
        'text': 'Limbo!',
    }
    request = build_request(server, data)

    response = urlopen(request)

    assert response.code == 202


def test_receive_server_without_channel(server):
    data = {
        'text': 'Which channel is this?!',
    }
    request = build_request(server, data)

    with pytest.raises(HTTPError) as excinfo:
        urlopen(request)

    assert excinfo.value.code == 400


def test_receive_server_without_text(server):
    data = {
        'channel': '#silence',
    }
    request = build_request(server, data)

    with pytest.raises(HTTPError) as excinfo:
        urlopen(request)

    assert excinfo.value.code == 400


# restricted access


def test_restricted_access_without_api_token(restricted_server):
    data = {
        'channel': '#internal',
        'text': 'I lost my wallet.',
    }
    request = build_request(restricted_server, data, api_token=None)

    with pytest.raises(HTTPError) as excinfo:
        urlopen(request)

    assert excinfo.value.code == 401


def test_restricted_access_with_invalid_api_token(restricted_server):
    data = {
        'channel': '#internal',
        'text': 'I can has access?!',
    }
    request = build_request(
        restricted_server,
        data,
        api_token='dwNlg-iDnDwx9lPr_DGaZzn2hjHx7_AK2UwUfqsrKr0',
    )

    with pytest.raises(HTTPError) as excinfo:
        urlopen(request)

    assert excinfo.value.code == 403


def test_restricted_access_with_valid_api_token(restricted_server):
    data = {
        'channel': '#internal',
        'text': 'Welcome to the club!',
    }
    request = build_request(
        restricted_server,
        data,
        api_token='qeV4Jf_PYxAySktCODORTKSH1gs117qJXwoqg5YoDBU',
    )

    response = urlopen(request)

    assert response.code == 202


# unknown URL path


def test_unsupported_url_path(server):
    url = get_server_url(server) + 'foo'
    request = Request(url, method='POST')

    with pytest.raises(HTTPError) as excinfo:
        urlopen(request)

    assert excinfo.value.code == 404


# response headers


def test_server_response_header(server):
    data = {
        'channel': '#curiosity',
        'text': 'Show me your web server version!',
    }
    request = build_request(server, data)

    response = urlopen(request)

    assert response.headers['Server'] == 'alertmanagermeshtastic'


# helpers


def build_request(server, data, *, api_token=None):
    url = get_server_url(server)

    data = json.dumps(data).encode('utf-8')

    headers = {'Content-Type': 'application/json'}
    if api_token:
        headers['Authorization'] = f'Token {api_token}'

    return Request(url, data=data, headers=headers, method='POST')


def get_server_url(server):
    server_host, server_port = server.server_address
    return f'http://{server_host}:{server_port}/'
