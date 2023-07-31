"""
alertmanagermeshtastic.meshtastic
~~~~~~~~~~~~~~~

Internet Relay Chat

:Copyright: 2007-2022 Jochen Kupperschmidt, Alexander Volz
:License: MIT, see LICENSE for details.
"""

from __future__ import annotations
import logging
import meshtastic, meshtastic.serial_interface

from dateutil import parser
from .config import MeshtasticConfig, MeshtasticConnection
import time


logger = logging.getLogger(__name__)


class Announcer:
    """An announcer."""

    def start(self) -> None:
        """Start the announcer."""

    def announce(self, alert: str) -> None:
        """Announce a message."""
        raise NotImplementedError()

    def shutdown(self) -> None:
        """Shut the announcer down."""


class MeshtasticAnnouncer(Announcer):
    """An announcer that writes messages to MESHTASTIC."""

    def __init__(
        self,
        connection: MeshtasticConnection,
    ) -> None:
        self.connection = connection

        self.meshtasticinterface = _create_meshtasticinterface(connection)

    def start(self) -> None:
        """Connect to the connection, in a separate thread."""
        logger.info(
            'Connecting to MESHTASTIC connection %s, the node is %d and messages will be sent %d times before failing',
            self.connection.tty,
            self.connection.nodeid,
            self.connection.maxsendingattempts,
        )

        # start_thread(self.meshtasticinterface.start)

    def announce(self, alert: str) -> None:
        """Announce a message."""
        try:
            try:
                message = self.formatalert(alert)

            except Exception as e:
                logger.error(
                    "\t Message formatting failed: %s",
                    e,
                )
                raise

            try:
                chunks = self.splitmessagesifnessecary(message)

            except Exception as e:
                logger.error(
                    "\t could not split in chunks: %s",
                    e,
                )
                raise

            for chunk in chunks:
                for attempt in range(self.connection.maxsendingattempts):
                    logger.debug(
                        "\tsending chunk attempt %d :%s ", attempt, chunk
                    )
                    try:
                        self.meshtasticinterface.sendText(
                            chunk,
                            self.connection.nodeid,
                            True,
                            False,
                            self.meshtasticinterface.getNode(
                                self.connection.nodeid, False
                            ).onAckNak,
                        )
                        self.meshtasticinterface.waitForAckNak()

                        start_time = time.time()
                        timeout = 60

                        while True:
                            # Check if value is True
                            if (
                                self.meshtasticinterface._acknowledgment.receivedAck
                            ):
                                print("got ack received from meshtastic")
                                break

                            # Check if timeout has been reached
                            if time.time() - start_time > timeout:
                                print("Timeout reached!")
                                raise Exception(
                                    "No ack received from meshtastic within the timeout"
                                )
                                break

                            # Sleep for a short period to avoid a busy wait
                            time.sleep(0.1)

                        logger.debug(
                            "\tsending chunk attempt %d success ", attempt
                        )
                        break
                    except Exception as e:
                        logger.error(
                            "\t chunk Attempt %d failed with error: %s",
                            attempt + 1,
                            e,
                        )
                        if attempt == self.connection.maxsendingattempts - 1:
                            raise

        except Exception as e:
            logger.error("\t send Attempt failed with error: %s", e)

    def splitmessagesifnessecary(self, message):
        chunk_size = 150
        if len(message) > chunk_size:
            logger.debug("\tMessage to big, split to chunks")
            chunks = [
                message[i : i + chunk_size]
                for i in range(0, len(message), chunk_size)
            ]
            return chunks
        else:
            logger.debug("\tMessage size okay")
            return [message]

    def formatalert(self, alert):
        message = "Status: " + alert["status"] + "\n"
        if "name" in alert["labels"]:
            message += (
                "Instance: "
                + alert["labels"]["instance"]
                + "("
                + alert["labels"]["name"]
                + ")\n"
            )
        elif "instance" in alert["labels"]:
            message += "Instance: " + alert["labels"]["instance"] + "\n"
        elif "alertname" in alert["labels"]:
            message += "Alert: " + alert["labels"]["alertname"] + "\n"
        if "info" in alert["annotations"]:
            message += "Info: " + alert["annotations"]["info"] + "\n"
        if "summary" in alert["annotations"]:
            message += "Summary: " + alert["annotations"]["summary"] + "\n"
        if 'description' in alert['annotations']:
            message += (
                "Description: " + alert['annotations']['description'] + "\n"
            )
        if alert["status"] == "resolved":
            correctdate = parser.parse(alert["endsAt"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            message += "Resolved: " + correctdate
        elif alert["status"] == "firing":
            correctdate = parser.parse(alert["startsAt"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            message += "Started: " + correctdate
        return message

    def shutdown(self) -> None:
        """Shut the announcer down."""
        self.meshtasticinterface.close()


class Meshtasticinterface(meshtastic.serial_interface.SerialInterface):
    """An MESHTASTIC Interface to forward messages to MESHTASTIC devices."""

    def get_version(self) -> str:
        """Return this on CTCP VERSION requests."""
        return 'alertmanagermeshtastic'


def _create_meshtasticinterface(
    connection: MeshtasticConnection,
) -> Meshtasticinterface:
    """Create a Interface."""

    meshtasticinterface = Meshtasticinterface(connection.tty)

    return meshtasticinterface


class DummyAnnouncer(Announcer):
    """An announcer that writes messages to STDOUT."""

    def announce(self, alert: str) -> None:
        """Announce a message."""
        logger.debug('%s> %s', alert)


def create_announcer(config: MeshtasticConfig) -> Announcer:
    """Create an announcer."""
    if config.connection is None:
        logger.info(
            'No MESHTASTIC connection specified; will write to STDOUT instead.'
        )
        return DummyAnnouncer()

    return MeshtasticAnnouncer(
        config.connection,
    )
