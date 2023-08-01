"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

import pytest

from alertmanagermeshtastic.meshtastic import MeshtasticChannel


@pytest.mark.parametrize(
    'channel, expected_name, expected_password',
    [
        (MeshtasticChannel('#example'),                         '#example',      None    ),
        (MeshtasticChannel('#example', password=None),          '#example',      None    ),
        (MeshtasticChannel('#headquarters', password='secret'), '#headquarters', 'secret'),
    ],
)
def test_meshtastic_channel_creation(channel, expected_name, expected_password):
    assert channel.name == expected_name
    assert channel.password == expected_password
