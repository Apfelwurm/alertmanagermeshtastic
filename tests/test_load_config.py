"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

from io import StringIO

from alertmanagermeshtastic.config import (
    HttpConfig,
    MeshtasticChannel,
    MeshtasticConfig,
    MeshtasticServer,
    load_config,
)


TOML_CONFIG = '''\
log_level = "warning"

[http]
host = "0.0.0.0"
port = 55555
api_tokens = ["qsSUx9KM-DBuDndUhGNi9_kxNHd08TypiHYM05ZTxVc"]

[meshtastic.server]
host = "orion.astrochat.test"
port = 6669
ssl = true
password = "ToTheStars!"
rate_limit = 0.5

[meshtastic.bot]
nickname = "SpaceCowboy"
realname = "Monsieur alertmanagermeshtastic"

[meshtastic]
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

    assert config.meshtastic == MeshtasticConfig(
        server=MeshtasticServer(
            host='orion.astrochat.test',
            port=6669,
            ssl=True,
            password='ToTheStars!',
            rate_limit=0.5,
        ),
        nickname='SpaceCowboy',
        realname='Monsieur alertmanagermeshtastic',
        commands=[
            'MODE SpaceCowboy +i',
        ],
        channels={
            MeshtasticChannel('#skyscreeners'),
            MeshtasticChannel('#elite-astrology', password='twinkle-twinkle'),
            MeshtasticChannel('#hubblebubble'),
        },
    )


TOML_CONFIG_WITH_DEFAULTS = '''\
[meshtastic.server]
host = "meshtastic.onlinetalk.test"

[meshtastic.bot]
nickname = "TownCrier"
'''


def test_load_config_with_defaults():
    toml = StringIO(TOML_CONFIG_WITH_DEFAULTS)

    config = load_config(toml)

    assert config.log_level == "DEBUG"

    assert config.http == HttpConfig(
        host='127.0.0.1',
        port=9119,
        api_tokens=set(),
        channel_tokens_to_channel_names={},
    )

    assert config.meshtastic == MeshtasticConfig(
        server=MeshtasticServer(
            host='meshtastic.onlinetalk.test',
            port=6667,
            ssl=False,
            password=None,
            rate_limit=None,
        ),
        nickname='TownCrier',
        realname='alertmanagermeshtastic',
        commands=[],
        channels=set(),
    )


TOML_CONFIG_WITHOUT_MESHTASTIC_SERVER_TABLE = '''\
[meshtastic.bot]
nickname = "Lokalrunde"
'''


def test_load_config_without_meshtastic_server_table():
    toml = StringIO(TOML_CONFIG_WITHOUT_MESHTASTIC_SERVER_TABLE)

    config = load_config(toml)

    assert config.meshtastic.server is None


TOML_CONFIG_WITHOUT_MESHTASTIC_SERVER_HOST = '''\
[meshtastic.server]

[meshtastic.bot]
nickname = "Lokalrunde"
'''


def test_load_config_without_meshtastic_server_host():
    toml = StringIO(TOML_CONFIG_WITHOUT_MESHTASTIC_SERVER_HOST)

    config = load_config(toml)

    assert config.meshtastic.server is None
