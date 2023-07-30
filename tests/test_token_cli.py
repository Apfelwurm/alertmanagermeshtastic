"""
:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

import pytest

from alertmanagermeshtastic.tokencli import generate_token


def test_generate_token():
    token = generate_token()

    assert token is not None
    assert len(token) >= 32  # Arbitrary number, but token shouldn't be short.


def test_generate_token_produces_different_results():
    sample_count = 10
    tokens = [generate_token() for _ in range(sample_count)]
    assert len(set(tokens)) == sample_count
