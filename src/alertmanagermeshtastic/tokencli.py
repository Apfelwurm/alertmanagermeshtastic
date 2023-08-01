"""
alertmanagermeshtastic.tokencli
~~~~~~~~~~~~~~~~~~~~

Command line tool to generate secret tokens

:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

from secrets import token_urlsafe


def generate_token() -> str:
    """Generate an random, secure, URL-safe token."""
    return token_urlsafe()


def main() -> None:
    """Write a secure token to STDOUT."""
    token = generate_token()
    print(token)


if __name__ == '__main__':
    main()
