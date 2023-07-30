"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

from threading import Thread

import pytest

from alertmanagermeshtastic.config import HttpConfig
from alertmanagermeshtastic.http import create_server


@pytest.fixture
def make_server():
    # Per default, bind to localhost on random user port.
    def _wrapper(host='', port=0, *, api_tokens=None):
        if api_tokens is None:
            api_tokens = set()
        config = HttpConfig(
            host,
            port,
            api_tokens=api_tokens,
            channel_tokens_to_channel_names={},
        )

        server = create_server(config)

        thread = Thread(target=server.handle_request)
        thread.start()

        return server

    return _wrapper
