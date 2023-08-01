"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

import pytest

from alertmanagermeshtastic.meshtastic import (
    create_announcer,
    DummyAnnouncer,
    MeshtasticAnnouncer,
    MeshtasticConfig,
    MeshtasticServer,
)


@pytest.mark.parametrize(
    'server, expected_type',
    [
        (MeshtasticServer('meshtastic.server.test'), MeshtasticAnnouncer),
        (None, DummyAnnouncer),
    ],
)
def test_create_announcer(server, expected_type):
    config = MeshtasticConfig(
        server=server,
        nickname='nick',
        realname='Nick',
        commands=[],
        channels=set(),
    )

    announcer = create_announcer(config)

    assert type(announcer) == expected_type
