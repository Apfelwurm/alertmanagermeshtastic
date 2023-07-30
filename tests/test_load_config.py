"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

from io import StringIO

from alertmanager-meshtastic.config import (
    HttpConfig,
    IrcChannel,
    IrcConfig,
    IrcServer,
    load_config,
)


TOML_CONFIG = '''\
log_level = "warning"

[http]
host = "0.0.0.0"
port = 55555
api_tokens = ["qsSUx9KM-DBuDndUhGNi9_kxNHd08TypiHYM05ZTxVc"]

[irc.server]
host = "orion.astrochat.test"
port = 6669
ssl = true
password = "ToTheStars!"
rate_limit = 0.5

[irc.bot]
nickname = "SpaceCowboy"
realname = "Monsieur alertmanager-meshtastic"

[irc]
commands = [
  "MODE SpaceCowboy +i",
]
channels = [
    { name = "#skyscreeners" },
    { name = "#elite-astrology", password = "twinkle-twinkle" },
    { name = "#hubblebubble" },
]
'''


def test_load_config():
    toml = StringIO(TOML_CONFIG)

    config = load_config(toml)

    assert config.log_level == "WARNING"

    assert config.http == HttpConfig(
        host='0.0.0.0',
        port=55555,
        api_tokens={'qsSUx9KM-DBuDndUhGNi9_kxNHd08TypiHYM05ZTxVc'},
        channel_tokens_to_channel_names={},
    )

    assert config.irc == IrcConfig(
        server=IrcServer(
            host='orion.astrochat.test',
            port=6669,
            ssl=True,
            password='ToTheStars!',
            rate_limit=0.5,
        ),
        nickname='SpaceCowboy',
        realname='Monsieur alertmanager-meshtastic',
        commands=[
            'MODE SpaceCowboy +i',
        ],
        channels={
            IrcChannel('#skyscreeners'),
            IrcChannel('#elite-astrology', password='twinkle-twinkle'),
            IrcChannel('#hubblebubble'),
        },
    )


TOML_CONFIG_WITH_DEFAULTS = '''\
[irc.server]
host = "irc.onlinetalk.test"

[irc.bot]
nickname = "TownCrier"
'''


def test_load_config_with_defaults():
    toml = StringIO(TOML_CONFIG_WITH_DEFAULTS)

    config = load_config(toml)

    assert config.log_level == "DEBUG"

    assert config.http == HttpConfig(
        host='127.0.0.1',
        port=8080,
        api_tokens=set(),
        channel_tokens_to_channel_names={},
    )

    assert config.irc == IrcConfig(
        server=IrcServer(
            host='irc.onlinetalk.test',
            port=6667,
            ssl=False,
            password=None,
            rate_limit=None,
        ),
        nickname='TownCrier',
        realname='alertmanager-meshtastic',
        commands=[],
        channels=set(),
    )


TOML_CONFIG_WITHOUT_IRC_SERVER_TABLE = '''\
[irc.bot]
nickname = "Lokalrunde"
'''


def test_load_config_without_irc_server_table():
    toml = StringIO(TOML_CONFIG_WITHOUT_IRC_SERVER_TABLE)

    config = load_config(toml)

    assert config.irc.server is None


TOML_CONFIG_WITHOUT_IRC_SERVER_HOST = '''\
[irc.server]

[irc.bot]
nickname = "Lokalrunde"
'''


def test_load_config_without_irc_server_host():
    toml = StringIO(TOML_CONFIG_WITHOUT_IRC_SERVER_HOST)

    config = load_config(toml)

    assert config.irc.server is None
