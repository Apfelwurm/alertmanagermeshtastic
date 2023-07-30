"""
alertmanager-meshtastic.config
~~~~~~~~~~~~~~~~~~

Configuration loading

:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

from __future__ import annotations
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Iterator, Optional

import rtoml


DEFAULT_HTTP_HOST = '127.0.0.1'
DEFAULT_HTTP_PORT = 8080
DEFAULT_IRC_SERVER_PORT = 6667
DEFAULT_IRC_REALNAME = 'alertmanager-meshtastic'


class ConfigurationError(Exception):
    """Indicates a configuration error."""


@dataclass(frozen=True)
class Config:
    log_level: str
    http: HttpConfig
    irc: IrcConfig


@dataclass(frozen=True)
class HttpConfig:
    """An HTTP receiver configuration."""

    host: str
    port: int
    api_tokens: set[str]
    channel_tokens_to_channel_names: dict[str, str]


@dataclass(frozen=True)
class IrcServer:
    """An IRC server."""

    host: str
    port: int = DEFAULT_IRC_SERVER_PORT
    ssl: bool = False
    password: Optional[str] = None
    rate_limit: Optional[float] = None


@dataclass(frozen=True, order=True)
class IrcChannel:
    """An IRC channel."""

    name: str
    password: Optional[str] = None


@dataclass(frozen=True)
class IrcConfig:
    """An IRC bot configuration."""

    server: Optional[IrcServer]
    nickname: str
    realname: str
    commands: list[str]
    channels: set[IrcChannel]


def load_config(path: Path) -> Config:
    """Load configuration from file."""
    data = rtoml.load(path)

    log_level = _get_log_level(data)
    http_config = _get_http_config(data)
    irc_config = _get_irc_config(data)

    return Config(
        log_level=log_level,
        http=http_config,
        irc=irc_config,
    )


def _get_log_level(data: dict[str, Any]) -> str:
    level = data.get('log_level', 'debug').upper()

    if level not in {'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'}:
        raise ConfigurationError(f'Unknown log level "{level}"')

    return level


def _get_http_config(data: dict[str, Any]) -> HttpConfig:
    data_http = data.get('http', {})

    host = data_http.get('host', DEFAULT_HTTP_HOST)
    port = int(data_http.get('port', DEFAULT_HTTP_PORT))
    api_tokens = set(data_http.get('api_tokens', []))
    channel_tokens_to_channel_names = _get_channel_tokens_to_channel_names(data)

    return HttpConfig(host, port, api_tokens, channel_tokens_to_channel_names)


def _get_channel_tokens_to_channel_names(
    data: dict[str, Any]
) -> dict[str, str]:
    channel_tokens_to_channel_names = {}

    for channel in data['irc'].get('channels', []):
        channel_name = channel['name']

        tokens = set(channel.get('tokens', []))
        for token in tokens:
            if token in channel_tokens_to_channel_names:
                raise ConfigurationError(
                    f'A channel token for channel "{channel_name}" '
                    'is already configured somewhere else.'
                )

            channel_tokens_to_channel_names[token] = channel_name

    return channel_tokens_to_channel_names


def _get_irc_config(data: dict[str, Any]) -> IrcConfig:
    data_irc = data['irc']

    server = _get_irc_server(data_irc)
    nickname = data_irc['bot']['nickname']
    realname = data_irc['bot'].get('realname', DEFAULT_IRC_REALNAME)
    commands = data_irc.get('commands', [])
    channels = set(_get_irc_channels(data_irc))

    return IrcConfig(
        server=server,
        nickname=nickname,
        realname=realname,
        commands=commands,
        channels=channels,
    )


def _get_irc_server(data_irc: Any) -> Optional[IrcServer]:
    data_server = data_irc.get('server')
    if data_server is None:
        return None

    host = data_server.get('host')
    if not host:
        return None

    port = int(data_server.get('port', DEFAULT_IRC_SERVER_PORT))
    ssl = data_server.get('ssl', False)
    password = data_server.get('password')
    rate_limit_str = data_server.get('rate_limit')
    rate_limit = float(rate_limit_str) if rate_limit_str else None

    return IrcServer(
        host=host, port=port, ssl=ssl, password=password, rate_limit=rate_limit
    )


def _get_irc_channels(data_irc: Any) -> Iterator[IrcChannel]:
    for channel in data_irc.get('channels', []):
        name = channel['name']
        password = channel.get('password')
        yield IrcChannel(name, password)
