"""
alertmanagermeshtastic.processor
~~~~~~~~~~~~~~~~~~~~~

Connect HTTP server and MESHTASTIC interface.

:Copyright: 2007-2022 Jochen Kupperschmidt
:Copyright: 2023 Alexander Volz
:License: MIT, see LICENSE for details.
"""

from __future__ import annotations
import logging
from collections import deque
from datetime import datetime, timedelta
import json

from typing import Any, Optional

from .config import Config
from .http import start_receive_server
from .meshtastic import create_announcer
from .signals import message_received, queue_size_updated, clear_queue_issued
import threading


logger = logging.getLogger(__name__)


class Processor:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.announcer = create_announcer(config.meshtastic, config.general)
        self.enabled_channel_names: set[str] = set()
        self.message_queue: deque = deque()
        self.queue_lock = threading.Lock()
        self.queue_empty_logged = False
        self.qn = 0

        # Up to this point, no signals must have been sent.
        self.connect_to_signals()
        # Signals are allowed be sent from here on.

    def connect_to_signals(self) -> None:
        message_received.connect(self.handle_message)
        clear_queue_issued.connect(self.handle_clear_queue)

    def handle_clear_queue(self, sender):
        logger.debug('\t clearing queue.... ')
        queue_entries = list(self.message_queue)
        self.message_queue.clear()

        with open('/tmp/queueclear', 'w') as f:
            json.dump(queue_entries, f)

        mock_alert = {
            "status": "quecleared",
            "fingerprint": "quecleared",
            "labels": {"alertname": "quecleared", "severity": "info"},
            "annotations": {
                "summary": "This is a alert for clearing the queue."
            },
        }
        self.handle_message(alert=mock_alert, sender=None)
        queue_size_updated.send(len(self.message_queue))

        logger.debug('\t clearing queue finished. ')

    def is_duplicate(self, alert: dict) -> bool:
        for item in self.message_queue:
            if (
                item["fingerprint"] == alert["fingerprint"]
                and item["status"] == alert["status"]
            ):
                return True
        return False

    def handle_message(
        self,
        sender: Optional[Any],
        *,
        alert: dict,
    ) -> None:
        """Log and announce an incoming message."""
        if not self.is_duplicate(alert):
            self.qn += 1
            alert["qn"] = self.qn
            alert["inputtime"] = (
                datetime.now()
                + timedelta(hours=self.config.general.inputtimeshift)
            ).strftime('%Y-%m-%d %H:%M:%S')
            logger.debug(
                '\t [%s][%s][%d][%d] put in queue',
                alert["fingerprint"],
                alert["inputtime"],
                self.config.general.inputtimeshift,
                alert["qn"],
            )
            self.message_queue.append(alert)
            queue_size_updated.send(len(self.message_queue))
        else:
            logger.debug(
                '\t [%s][%s] duplicate message, not adding to queue',
                alert["fingerprint"],
                alert["status"],
            )

    def announce_message(self, alert: dict) -> None:
        """Announce message on MESHTASTIC."""
        self.announcer.announce(alert)

    def process_queue(self, timeout_seconds: Optional[int] = None) -> None:
        """Process a message from the queue."""

        if len(self.message_queue) == 0:
            if not self.queue_empty_logged:
                logger.debug(
                    '\t Messages in queue: %d', len(self.message_queue)
                )
                self.queue_empty_logged = True
        else:
            self.queue_empty_logged = False
            logger.debug('\t Messages in queue: %d', len(self.message_queue))
            with self.queue_lock:
                if self.message_queue:
                    alert = self.message_queue.popleft()
                    logger.debug(
                        '\t [%s][%d] processing message ',
                        alert["fingerprint"],
                        alert["qn"],
                    )
                    self.announce_message(alert)
                    queue_size_updated.send(len(self.message_queue))

    def run(self) -> None:
        """Run the main loop."""
        self.announcer.start()
        start_receive_server(self.config.http)

        logger.info('\t Starting to process queue ...')
        try:
            while True:
                self.process_queue()
        except KeyboardInterrupt:
            pass

        logger.info('\t Shutting down ...')
        self.announcer.shutdown()


def start(config: Config) -> None:
    """Start the MESHTASTIC interface and the HTTP listen server."""
    processor = Processor(config)
    processor.run()
