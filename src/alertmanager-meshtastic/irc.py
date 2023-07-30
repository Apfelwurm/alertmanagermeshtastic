"""
alertmanager-meshtastic.irc
~~~~~~~~~~~~~~~

Internet Relay Chat

:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

from __future__ import annotations
import logging
import ssl
from typing import Optional

from irc.bot import ServerSpec, SingleServerIRCBot
from irc.connection import Factory
from jaraco.stream.buffer import LenientDecodingLineBuffer

from .config import IrcChannel, IrcConfig, IrcServer
from .signals import irc_channel_joined
from .util import start_thread


logger = logging.getLogger(__name__)


class Announcer:
    """An announcer."""

    def start(self) -> None:
        """Start the announcer."""

    def announce(self, channel_name: str, text: str) -> None:
        """Announce a message."""
        raise NotImplementedError()

    def shutdown(self) -> None:
        """Shut the announcer down."""


class IrcAnnouncer(Announcer):
    """An announcer that writes messages to IRC."""

    def __init__(
        self,
        server: IrcServer,
        nickname: str,
        realname: str,
        commands: list[str],
        channels: set[IrcChannel],
    ) -> None:
        self.server = server
        self.commands = commands
        self.channels = channels

        self.bot = _create_bot(server, nickname, realname)
        self.bot.on_welcome = self._on_welcome

    def start(self) -> None:
        """Connect to the server, in a separate thread."""
        logger.info(
            'Connecting to IRC server %s:%d ...',
            self.server.host,
            self.server.port,
        )

        start_thread(self.bot.start)

    def _on_welcome(self, conn, event) -> None:
        """Join channels after connect."""
        logger.info(
            'Connected to IRC server %s:%d.', *conn.socket.getpeername()
        )

        self._send_commands(conn)
        self._join_channels(conn)

    def _send_commands(self, conn):
        """Send custom commands after having been welcomed by the server."""
        for command in self.commands:
            conn.send_raw(command)

    def _join_channels(self, conn):
        """Join the configured channels."""
        channels = sorted(self.channels)
        logger.info('Channels to join: %s', ', '.join(c.name for c in channels))

        for channel in channels:
            logger.info('Joining channel %s ...', channel.name)
            conn.join(channel.name, channel.password or '')

    def announce(self, channel_name: str, text: str) -> None:
        """Announce a message."""
        self.bot.connection.privmsg(channel_name, text)

    def shutdown(self) -> None:
        """Shut the announcer down."""
        self.bot.disconnect('Bye.')


class Bot(SingleServerIRCBot):
    """An IRC bot to forward messages to IRC channels."""

    def get_version(self) -> str:
        """Return this on CTCP VERSION requests."""
        return 'alertmanager-meshtastic'

    def on_nicknameinuse(self, conn, event) -> None:
        """Choose another nickname if conflicting."""
        self._nickname += '_'
        conn.nick(self._nickname)

    def on_join(self, conn, event) -> None:
        """Successfully joined channel."""
        joined_nick = event.source.nick
        channel_name = event.target

        if joined_nick == self._nickname:
            logger.info('Joined IRC channel: %s', channel_name)
            irc_channel_joined.send(channel_name=channel_name)

    def on_badchannelkey(self, conn, event) -> None:
        """Channel could not be joined due to wrong password."""
        channel_name = event.arguments[0]
        logger.warning('Cannot join channel %s (bad key).', channel_name)


def _create_bot(server: IrcServer, nickname: str, realname: str) -> Bot:
    """Create a bot."""
    server_spec = ServerSpec(server.host, server.port, server.password)
    factory = Factory(wrapper=ssl.wrap_socket) if server.ssl else Factory()

    bot = Bot([server_spec], nickname, realname, connect_factory=factory)

    _set_rate_limit(bot.connection, server.rate_limit)

    # Avoid `UnicodeDecodeError` on non-UTF-8 messages.
    bot.connection.buffer_class = LenientDecodingLineBuffer

    return bot


def _set_rate_limit(connection, rate_limit: Optional[float]) -> None:
    """Set rate limit."""
    if rate_limit is not None:
        logger.info(
            'IRC send rate limit set to %.2f messages per second.',
            rate_limit,
        )
        connection.set_rate_limit(rate_limit)
    else:
        logger.info('No IRC send rate limit set.')


class DummyAnnouncer(Announcer):
    """An announcer that writes messages to STDOUT."""

    def __init__(self, channels: set[IrcChannel]) -> None:
        self.channels = channels

    def start(self) -> None:
        """Start the announcer."""
        # Fake channel joins.
        for channel in sorted(self.channels):
            irc_channel_joined.send(channel_name=channel.name)

    def announce(self, channel_name: str, text: str) -> None:
        """Announce a message."""
        logger.debug('%s> %s', channel_name, text)


def create_announcer(config: IrcConfig) -> Announcer:
    """Create an announcer."""
    if config.server is None:
        logger.info('No IRC server specified; will write to STDOUT instead.')
        return DummyAnnouncer(config.channels)

    return IrcAnnouncer(
        config.server,
        config.nickname,
        config.realname,
        config.commands,
        config.channels,
    )
