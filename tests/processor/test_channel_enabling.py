"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

from alertmanager-meshtastic.config import Config, HttpConfig, IrcConfig
from alertmanager-meshtastic.processor import Processor
from alertmanager-meshtastic.signals import irc_channel_joined


def test_channel_enabling_on_join_signal():
    processor = create_processor()

    assert '#example1' not in processor.enabled_channel_names
    assert '#example2' not in processor.enabled_channel_names

    irc_channel_joined.send(channel_name='#example1')

    assert '#example1' in processor.enabled_channel_names
    assert '#example2' not in processor.enabled_channel_names

    irc_channel_joined.send(channel_name='#example2')

    assert '#example1' in processor.enabled_channel_names
    assert '#example2' in processor.enabled_channel_names


def create_processor():
    http_config = HttpConfig(
        host='127.0.0.1',
        port='8080',
        api_tokens=set(),
        channel_tokens_to_channel_names={},
    )

    irc_config = IrcConfig(
        server=None,
        nickname='nick',
        realname='Nick',
        commands=[],
        channels=set(),
    )

    config = Config(log_level=None, http=http_config, irc=irc_config)

    return Processor(config)
