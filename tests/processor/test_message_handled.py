"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

import pytest

from alertmanagermeshtastic.config import Config, HttpConfig, MeshtasticConfig
from alertmanagermeshtastic.processor import Processor
from alertmanagermeshtastic.signals import meshtastic_channel_joined, message_received


@pytest.fixture
def processor():
    http_config = HttpConfig(
        'localhost',
        8080,
        api_tokens=set(),
        channel_tokens_to_channel_names={},
    )

    meshtastic_config = MeshtasticConfig(
        server=None,
        nickname='Nick',
        realname='Nick',
        commands=[],
        channels=set(),
    )

    config = Config(log_level="debug", http=http_config, meshtastic=meshtastic_config)

    return Processor(config)


def test_message_handled(processor):
    channel_name = '#foo'
    text = 'Knock, knock.'

    received_signal_data = []

    def announce(channel_name, text):
        received_signal_data.append((channel_name, text))

    processor.announcer.announce = announce

    fake_channel_join(channel_name)

    send_message_received_signal(channel_name, text)

    processor.process_queue(timeout_seconds=1)

    assert received_signal_data == [
        (channel_name, text),
    ]


def fake_channel_join(channel_name):
    meshtastic_channel_joined.send(channel_name=channel_name)


def send_message_received_signal(channel_name, text):
    source_ip_address = '127.0.0.1'
    message_received.send(
        None,
        channel_name=channel_name,
        text=text,
        source_ip_address=source_ip_address,
    )
