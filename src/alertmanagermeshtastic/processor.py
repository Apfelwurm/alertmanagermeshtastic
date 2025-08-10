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
import time

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

        # Per-node queues for message tracking and retry logic
        self.node_queues: dict[int, deque] = {}
        self.node_locks: dict[int, threading.Lock] = {}
        self.node_failure_counts: dict[int, int] = {}
        self.node_last_failure: dict[int, float] = {}

        # Initialize per-node structures
        if (
            config.meshtastic.connection
            and config.meshtastic.connection.nodeids
        ):
            for nodeid in config.meshtastic.connection.nodeids:
                self.node_queues[nodeid] = deque()
                self.node_locks[nodeid] = threading.Lock()
                self.node_failure_counts[nodeid] = 0
                self.node_last_failure[nodeid] = 0
        else:
            # Fallback for DummyAnnouncer or no connection - use single "dummy" node
            dummy_nodeid = 0
            self.node_queues[dummy_nodeid] = deque()
            self.node_locks[dummy_nodeid] = threading.Lock()
            self.node_failure_counts[dummy_nodeid] = 0
            self.node_last_failure[dummy_nodeid] = 0

        self.total_queue_size = 0
        self.queue_empty_logged = False
        self.qn = 0
        self._processing_lock = threading.Lock()

        # Up to this point, no signals must have been sent.
        self.connect_to_signals()
        # Signals are allowed be sent from here on.

    def connect_to_signals(self) -> None:
        message_received.connect(self.handle_message)
        clear_queue_issued.connect(self.handle_clear_queue)

    def handle_clear_queue(self, sender):
        logger.debug('\t clearing all node queues.... ')
        queue_entries = []

        # Clear all node queues
        for nodeid in self.node_queues:
            with self.node_locks[nodeid]:
                queue_entries.extend(list(self.node_queues[nodeid]))
                self.node_queues[nodeid].clear()

        # Update total queue size
        self.total_queue_size = 0

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
        queue_size_updated.send(self.total_queue_size)

        logger.debug('\t clearing all node queues finished. ')

    # TODO: this is bad, since this should be handled per queue, so that a queue that runs full does not prevent the message to other queues where it is not available
    def is_duplicate(self, alert: dict) -> bool:
        # Check for duplicates across all node queues
        for nodeid in self.node_queues:
            for item in self.node_queues[nodeid]:
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
                '\t [%s][%s][%d][%d] adding to all node queues',
                alert["fingerprint"],
                alert["inputtime"],
                self.config.general.inputtimeshift,
                alert["qn"],
            )

            # Add message to all node queues
            for nodeid in self.node_queues:
                with self.node_locks[nodeid]:
                    # Create a copy for each node to avoid shared state issues
                    node_alert = alert.copy()
                    self.node_queues[nodeid].append(node_alert)

            # Update total queue size
            self.total_queue_size = sum(
                len(queue) for queue in self.node_queues.values()
            )
            queue_size_updated.send(self.total_queue_size)
        else:
            logger.debug(
                '\t [%s][%s] duplicate message, not adding to queues',
                alert["fingerprint"],
                alert["status"],
            )

    def announce_message_to_node(self, alert: dict, nodeid: int) -> bool:
        """Announce message to a specific node. Returns True if successful."""
        try:
            if hasattr(self.announcer, 'announce_to_node'):
                self.announcer.announce_to_node(alert, nodeid)
            else:
                # Fallback for announcers that don't support per-node messaging
                self.announcer.announce(alert)

            # Reset failure count on success
            self.node_failure_counts[nodeid] = 0
            return True

        except Exception as e:
            # Track failure
            self.node_failure_counts[nodeid] += 1
            self.node_last_failure[nodeid] = time.time()

            logger.error(
                '\t [%s][%d][node:%d] Failed to announce message (failure #%d): %s',
                alert["fingerprint"],
                alert["qn"],
                nodeid,
                self.node_failure_counts[nodeid],
                e,
            )
            return False

    def should_skip_node(self, nodeid: int) -> bool:
        """Check if we should temporarily skip a node due to repeated failures."""
        failure_count = self.node_failure_counts[nodeid]

        # Get configuration values, with fallbacks if no connection config exists
        if self.config.meshtastic.connection:
            failure_threshold = (
                self.config.meshtastic.connection.failure_threshold
            )
            base_backoff = self.config.meshtastic.connection.base_backoff_time
            max_backoff = self.config.meshtastic.connection.max_backoff_time
            multiplier = self.config.meshtastic.connection.backoff_multiplier
        else:
            # Fallback values for when no connection config exists (e.g., DummyAnnouncer)
            from .config import (
                DEFAULT_MESHTASTIC_FAILURE_THRESHOLD,
                DEFAULT_MESHTASTIC_BASE_BACKOFF_TIME,
                DEFAULT_MESHTASTIC_MAX_BACKOFF_TIME,
                DEFAULT_MESHTASTIC_BACKOFF_MULTIPLIER,
            )

            failure_threshold = DEFAULT_MESHTASTIC_FAILURE_THRESHOLD
            base_backoff = DEFAULT_MESHTASTIC_BASE_BACKOFF_TIME
            max_backoff = DEFAULT_MESHTASTIC_MAX_BACKOFF_TIME
            multiplier = DEFAULT_MESHTASTIC_BACKOFF_MULTIPLIER

        # Skip node if it has failed multiple times recently
        if failure_count >= failure_threshold:
            time_since_failure = time.time() - self.node_last_failure[nodeid]
            # Wait longer for nodes with more failures using exponential backoff
            wait_time = min(
                base_backoff
                * (multiplier ** (failure_count - failure_threshold)),
                max_backoff,
            )

            if time_since_failure < wait_time:
                logger.debug(
                    '\t [node:%d] Skipping due to recent failures (%d). Retry in %ds',
                    nodeid,
                    failure_count,
                    wait_time - time_since_failure,
                )
                return True

        return False

    def process_queue(self) -> None:
        """Process messages using resilient sequential delivery."""
        with self._processing_lock:
            processed_any = False

            # Process each node's queue
            for nodeid in self.node_queues:
                if self.should_skip_node(nodeid):
                    continue

                with self.node_locks[nodeid]:
                    if self.node_queues[nodeid]:
                        alert = self.node_queues[nodeid].popleft()
                        processed_any = True

                        logger.debug(
                            '\t [%s][%d][node:%d] processing message',
                            alert["fingerprint"],
                            alert["qn"],
                            nodeid,
                        )

                        # Try to send the message
                        success = self.announce_message_to_node(alert, nodeid)

                        if not success:
                            # Put message back at the front for retry later
                            self.node_queues[nodeid].appendleft(alert)
                            logger.debug(
                                '\t [%s][%d][node:%d] Message queued for retry',
                                alert["fingerprint"],
                                alert["qn"],
                                nodeid,
                            )
                        else:
                            logger.debug(
                                '\t [%s][%d][node:%d] Message sent successfully',
                                alert["fingerprint"],
                                alert["qn"],
                                nodeid,
                            )

            # Update total queue size
            self.total_queue_size = sum(
                len(queue) for queue in self.node_queues.values()
            )
            queue_size_updated.send(self.total_queue_size)

            if not processed_any:
                if not self.queue_empty_logged:
                    logger.debug(
                        '\t All queues empty or nodes temporarily unavailable'
                    )
                    self.queue_empty_logged = True
                time.sleep(5)
            else:
                self.queue_empty_logged = False

    def run(self) -> None:
        """Run the main loop."""
        self.announcer.start()
        start_receive_server(self.config.http)

        logger.info('\t Starting resilient sequential queue processing ...')

        try:
            while True:
                # Process queues in a resilient sequential manner
                # Failed nodes are temporarily skipped, others continue
                self.process_queue()
        except KeyboardInterrupt:
            pass

        logger.info('\t Shutting down ...')
        self.announcer.shutdown()


def start(config: Config) -> None:
    """Start the MESHTASTIC interface and the HTTP listen server."""
    processor = Processor(config)
    processor.run()
