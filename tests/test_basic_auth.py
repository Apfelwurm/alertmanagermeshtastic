"""
Test basic authentication functionality.

:Copyright: 2023 Alexander Volz
:License: MIT, see LICENSE for details.
"""

import base64
from http import HTTPStatus
import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from alertmanagermeshtastic.config import HttpConfig
from alertmanagermeshtastic.http import create_app


def test_basic_auth_not_configured():
    """Test that requests are allowed when no basic auth is configured."""
    config = HttpConfig(
        host="127.0.0.1",
        port=9119,
        clearsecret="test_secret",
        basic_auth_username=None,
        basic_auth_password=None
    )
    app = create_app(config)
    client = Client(app, Response)
    
    test_data = b'{"alerts": [{"fingerprint": "test123", "status": "firing", "labels": {"alertname": "test"}, "annotations": {"summary": "Test alert"}}]}'
    
    response = client.post('/alert', data=test_data, content_type='application/json')
    assert response.status_code == HTTPStatus.OK


def test_basic_auth_missing_credentials():
    """Test that requests without auth are rejected when basic auth is configured."""
    config = HttpConfig(
        host="127.0.0.1",
        port=9119,
        clearsecret="test_secret",
        basic_auth_username="testuser",
        basic_auth_password="testpass"
    )
    app = create_app(config)
    client = Client(app, Response)
    
    test_data = b'{"alerts": [{"fingerprint": "test123", "status": "firing", "labels": {"alertname": "test"}, "annotations": {"summary": "Test alert"}}]}'
    
    response = client.post('/alert', data=test_data, content_type='application/json')
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert 'WWW-Authenticate' in response.headers
    assert response.headers['WWW-Authenticate'] == 'Basic realm="alertmanagermeshtastic"'


def test_basic_auth_wrong_credentials():
    """Test that requests with wrong credentials are rejected."""
    config = HttpConfig(
        host="127.0.0.1",
        port=9119,
        clearsecret="test_secret",
        basic_auth_username="testuser",
        basic_auth_password="testpass"
    )
    app = create_app(config)
    client = Client(app, Response)
    
    test_data = b'{"alerts": [{"fingerprint": "test123", "status": "firing", "labels": {"alertname": "test"}, "annotations": {"summary": "Test alert"}}]}'
    
    # Test wrong username
    auth_header = base64.b64encode(b"wronguser:testpass").decode('utf-8')
    headers = [("Authorization", f"Basic {auth_header}")]
    
    response = client.post('/alert', data=test_data, content_type='application/json', headers=headers)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    # Test wrong password
    auth_header = base64.b64encode(b"testuser:wrongpass").decode('utf-8')
    headers = [("Authorization", f"Basic {auth_header}")]
    
    response = client.post('/alert', data=test_data, content_type='application/json', headers=headers)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_basic_auth_correct_credentials():
    """Test that requests with correct credentials are accepted."""
    config = HttpConfig(
        host="127.0.0.1",
        port=9119,
        clearsecret="test_secret",
        basic_auth_username="testuser",
        basic_auth_password="testpass"
    )
    app = create_app(config)
    client = Client(app, Response)
    
    test_data = b'{"alerts": [{"fingerprint": "test123", "status": "firing", "labels": {"alertname": "test"}, "annotations": {"summary": "Test alert"}}]}'
    
    auth_header = base64.b64encode(b"testuser:testpass").decode('utf-8')
    headers = [("Authorization", f"Basic {auth_header}")]
    
    response = client.post('/alert', data=test_data, content_type='application/json', headers=headers)
    assert response.status_code == HTTPStatus.OK


def test_basic_auth_malformed_header():
    """Test that malformed auth headers are rejected."""
    config = HttpConfig(
        host="127.0.0.1",
        port=9119,
        clearsecret="test_secret",
        basic_auth_username="testuser",
        basic_auth_password="testpass"
    )
    app = create_app(config)
    client = Client(app, Response)
    
    test_data = b'{"alerts": [{"fingerprint": "test123", "status": "firing", "labels": {"alertname": "test"}, "annotations": {"summary": "Test alert"}}]}'
    
    # Test various malformed headers
    malformed_headers_list = [
        [("Authorization", "Basic")],  # Missing credentials
        [("Authorization", "Bearer token")],  # Wrong auth type
        [("Authorization", "Basic invalid_base64")],  # Invalid base64
        [("Authorization", "Basic " + base64.b64encode(b"no_colon").decode('utf-8'))],  # No colon separator
    ]
    
    for headers in malformed_headers_list:
        response = client.post('/alert', data=test_data, content_type='application/json', headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_basic_auth_only_affects_alert_endpoint():
    """Test that basic auth only affects the /alert endpoint, not others."""
    config = HttpConfig(
        host="127.0.0.1",
        port=9119,
        clearsecret="test_secret",
        basic_auth_username="testuser",
        basic_auth_password="testpass"
    )
    app = create_app(config)
    client = Client(app, Response)
    
    # /metrics should still be accessible without auth
    response = client.get('/metrics')
    assert response.status_code == HTTPStatus.OK
    
    # /clear_queue should still use its own secret-based auth
    response = client.get('/clear_queue?secret=test_secret')
    assert response.status_code == HTTPStatus.OK
    
    response = client.get('/clear_queue?secret=wrong_secret')
    assert response.status_code == HTTPStatus.FORBIDDEN