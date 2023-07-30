"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

import pytest

from alertmanager-meshtastic.irc import (
    create_announcer,
    DummyAnnouncer,
    IrcAnnouncer,
    IrcConfig,
    IrcServer,
)


@pytest.mark.parametrize(
    'server, expected_type',
    [
        (IrcServer('irc.server.test'), IrcAnnouncer),
        (None, DummyAnnouncer),
    ],
)
def test_create_announcer(server, expected_type):
    config = IrcConfig(
        server=server,
        nickname='nick',
        realname='Nick',
        commands=[],
        channels=set(),
    )

    announcer = create_announcer(config)

    assert type(announcer) == expected_type
