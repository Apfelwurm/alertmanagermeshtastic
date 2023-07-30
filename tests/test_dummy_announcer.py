"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

import pytest

from alertmanagermeshtastic.meshtastic import create_announcer, MeshtasticChannel, MeshtasticConfig
from alertmanagermeshtastic.signals import meshtastic_channel_joined


@pytest.fixture
def config():
    channels = {MeshtasticChannel('#one'), MeshtasticChannel('#two')}

    return MeshtasticConfig(
        server=None,
        nickname='nick',
        realname='Nick',
        commands=[],
        channels=channels,
    )


@pytest.fixture
def announcer(config):
    announcer = create_announcer(config)

    yield announcer

    announcer.shutdown()


def test_fake_channel_joins(announcer):
    received_signal_data = []

    @meshtastic_channel_joined.connect
    def handle_meshtastic_channel_joined(sender, **data):
        received_signal_data.append(data)

    announcer.start()

    assert received_signal_data == [
        {'channel_name': '#one'},
        {'channel_name': '#two'},
    ]
