"""
alertmanagermeshtastic.processor
~~~~~~~~~~~~~~~~~~~~~

Connect HTTP server and MESHTASTIC bot.

:Copyright: 2007-2022 Jochen Kupperschmidt
:License: MIT, see LICENSE for details.
"""

from __future__ import annotations
import logging
from queue import SimpleQueue
from typing import Any, Optional

from .config import Config
from .http import start_receive_server
from .meshtastic import create_announcer
from .signals import message_received


logger = logging.getLogger(__name__)


class Processor:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.announcer = create_announcer(config.meshtastic)
        self.enabled_channel_names: set[str] = set()
        self.message_queue: SimpleQueue = SimpleQueue()

        # Up to this point, no signals must have been sent.
        self.connect_to_signals()
        # Signals are allowed be sent from here on.

    def connect_to_signals(self) -> None:
        message_received.connect(self.handle_message)

    def enable_channel(self, sender, *, channel_name=None) -> None:
        logger.info('Enabled forwarding to channel %s.', channel_name)
        self.enabled_channel_names.add(channel_name)

    def handle_message(
        self,
        sender: Optional[Any],
        *,
        channel_name: str,
        text: str,
        source_ip_address: Optional[str] = None,
    ) -> None:
        """Log and announce an incoming message."""
        logger.debug(
            'Received message from %s for channel %s with text "%s".',
            source_ip_address or 'unknown address',
            channel_name,
            text,
        )

        self.message_queue.put((channel_name, text))

    def announce_message(self, channel_name: str, text: str) -> None:
        """Announce message on MESHTASTIC."""
        if channel_name not in self.enabled_channel_names:
            logger.warning(
                'Could not send message to channel %s, not joined.',
                channel_name,
            )
            return

        self.announcer.announce(channel_name, text)

    def process_queue(self, timeout_seconds: Optional[int] = None) -> None:
        """Process a message from the queue."""
        channel_name, text = self.message_queue.get(timeout=timeout_seconds)
        self.announce_message(channel_name, text)

    def run(self) -> None:
        """Run the main loop."""
        self.announcer.start()
        start_receive_server(self.config.http)

        logger.info('Starting to process queue ...')
        try:
            while True:
                self.process_queue()
        except KeyboardInterrupt:
            pass

        logger.info('Shutting down ...')
        self.announcer.shutdown()


def start(config: Config) -> None:
    """Start the MESHTASTIC bot and the HTTP listen server."""
    processor = Processor(config)
    processor.run()
