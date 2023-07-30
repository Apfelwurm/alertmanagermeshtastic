"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

from irc.client import Event, NickMask, ServerConnection
import pytest

from alertmanager-meshtastic.irc import create_announcer, IrcChannel, IrcConfig, IrcServer
from alertmanager-meshtastic.signals import irc_channel_joined


@pytest.fixture
def config():
    server = IrcServer('irc.server.test')

    channels = {IrcChannel('#one'), IrcChannel('#two')}

    return IrcConfig(
        server=server,
        nickname='nick',
        realname='Nick',
        commands=[],
        channels=channels,
    )


@pytest.fixture
def bot(config):
    announcer = create_announcer(config)

    yield announcer.bot

    announcer.shutdown()


@pytest.fixture
def nickmask(config):
    return NickMask(f'{config.nickname}!{config.nickname}@{config.server.host}')


def test_get_version(bot):
    assert bot.get_version() == 'alertmanager-meshtastic'


def test_channel_joins(config, bot, nickmask, monkeypatch):
    class FakeSocket:
        def getpeername(self):
            return ('10.0.0.99', 6667)

    socket = FakeSocket()
    conn = ServerConnection(None)

    welcome_event = Event(
        type='welcome', source=config.server.host, target=config.nickname
    )

    def join(self, channel, key=''):
        join_event = Event(type='join', source=nickmask, target=channel)
        bot.on_join(conn, join_event)

    received_signal_data = []

    @irc_channel_joined.connect
    def handle_irc_channel_joined(sender, **data):
        received_signal_data.append(data)

    with monkeypatch.context() as mpc:
        mpc.setattr(ServerConnection, 'socket', socket)
        mpc.setattr(ServerConnection, 'join', join)
        bot.on_welcome(conn, welcome_event)

    assert received_signal_data == [
        {'channel_name': '#one'},
        {'channel_name': '#two'},
    ]
