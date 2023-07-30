"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

import pytest

from alertmanager-meshtastic.irc import create_announcer, IrcChannel, IrcConfig
from alertmanager-meshtastic.signals import irc_channel_joined


@pytest.fixture
def config():
    channels = {IrcChannel('#one'), IrcChannel('#two')}

    return IrcConfig(
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

    @irc_channel_joined.connect
    def handle_irc_channel_joined(sender, **data):
        received_signal_data.append(data)

    announcer.start()

    assert received_signal_data == [
        {'channel_name': '#one'},
        {'channel_name': '#two'},
    ]
