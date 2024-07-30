"""
alertmanagermeshtastic.meshtastic
~~~~~~~~~~~~~~~

Meshtastic connection

:Copyright: 2007-2022 Jochen Kupperschmidt
:Copyright: 2023 Alexander Volz
:License: MIT, see LICENSE for details.
"""

from __future__ import annotations
import logging
import meshtastic, meshtastic.serial_interface

from dateutil import parser
from datetime import timedelta
from .config import MeshtasticConfig, MeshtasticConnection, GeneralConfig
import time

from pubsub import pub
from .signals import meshtastic_connected


logger = logging.getLogger(__name__)


class Announcer:
    """An announcer."""

    def start(self) -> None:
        """Start the announcer."""

    def announce(self, alert: dict) -> None:
        """Announce a message."""
        raise NotImplementedError()

    def shutdown(self) -> None:
        """Shut the announcer down."""


class MeshtasticAnnouncer(Announcer):
    """An announcer that writes messages to MESHTASTIC."""

    def __init__(
        self,
        connection: MeshtasticConnection,
        generalconfig: GeneralConfig,
    ) -> None:
        self.connection = connection
        self.generalconfig = generalconfig

        self.meshtasticinterface = _create_meshtasticinterface(connection)

    def _onconnect(self, topic=pub.AUTO_TOPIC, interface=None):
        meshtastic_connected.send(True)
        pub.subscribe(self._onconnectionlost, "meshtastic.connection.lost")
        logger.debug("\t Connected to meshtastic")

    def _onconnectionlost(self, topic=pub.AUTO_TOPIC, interface=None):
        meshtastic_connected.send(False)
        logger.error("Connection Lost! try deleting and reconnecting interface")
        pub.unsubscribe(self._onconnectionlost, "meshtastic.connection.lost")

        if hasattr(self, 'meshtasticinterface'):
            try:
                logger.error("Closing interface...")
                self.meshtasticinterface.close()
                logger.error("Interface Closed!")
            except Exception as e:
                logger.error("Failed to close meshtastic interface: %s", e)
            finally:
                logger.error("Deleting Interface...")
                del self.meshtasticinterface
                logger.error("Interface deleted!")

        while True:
            try:
                logger.error("Recreating interface...")
                self.meshtasticinterface = _create_meshtasticinterface(
                    self.connection
                )
                logger.error("interface recreated!")
                break
            except Exception as e:
                logger.error(
                    "\t Connnection to meshtastic failed with error: %s , retry in 2 seconds",
                    e,
                )
                time.sleep(2)

    def start(self) -> None:
        """Connect to the connection, in a separate thread."""
        logger.info(
            '\t Connecting to MESHTASTIC connection %s, the node is %d and messages will be sent %d times with timeout %d before failing',
            self.connection.tty,
            self.connection.nodeid,
            self.connection.maxsendingattempts,
            self.connection.timeout,
        )
        pub.subscribe(self._onconnect, "meshtastic.connection.established")
        # start_thread(self.meshtasticinterface.start)

    def announce(self, alert: dict) -> None:
        """Announce a message."""
        try:
            try:
                message = self.formatalert(alert)

            except Exception as e:
                logger.error(
                    "\t [%s][%d] Message formatting failed: %s",
                    alert["fingerprint"],
                    alert["qn"],
                    e,
                )
                raise

            try:
                chunks = self.splitmessagesifnessecary(message, alert)
                total_chunks = len(chunks)
                logger.debug(
                    "\t [%s][%d] splitted in %d chunks",
                    alert["fingerprint"],
                    alert["qn"],
                    total_chunks,
                )

            except Exception as e:
                logger.error(
                    "\t [%s][%d] could not split in chunks: %s",
                    alert["fingerprint"],
                    alert["qn"],
                    e,
                )
                raise

            for index, chunk in enumerate(chunks):
                for attempt in range(self.connection.maxsendingattempts):
                    logger.debug(
                        "\t [%s][%d][%d] sending attempt %d ",
                        alert["fingerprint"],
                        alert["qn"],
                        index,
                        attempt,
                    )
                    try:
                        while not hasattr(self, 'meshtasticinterface'):
                            time.sleep(2)

                        self.meshtasticinterface.sendText(
                            text=str(alert["qn"])
                            + ":"
                            + str(index + 1)
                            + "/"
                            + str(total_chunks)
                            + "\n"
                            + chunk,
                            destinationId=self.connection.nodeid,
                            wantAck=True,
                            wantResponse=False,
                            onResponse=self.meshtasticinterface.getNode(
                                self.connection.nodeid, False
                            ).onAckNak,
                        )

                        ack = False

                        # Check acknowledgment in while until Nak, Ack or ImplAck is set or the timeout is received
                        start_time = time.time()
                        while (
                            time.time() - start_time < self.connection.timeout
                        ):
                            if (
                                self.meshtasticinterface._acknowledgment.receivedAck
                                or self.meshtasticinterface._acknowledgment.receivedImplAck
                            ):
                                ack = True
                                break

                            if (
                                self.meshtasticinterface._acknowledgment.receivedNak
                            ):
                                break
                            time.sleep(0.5)

                        # Reset acknowledgement after checking it ourselves
                        self.meshtasticinterface._acknowledgment.reset()

                        if ack:
                            logger.debug(
                                "\t [%s][%d][%d] got ack received from meshtastic on attempt %d",
                                alert["fingerprint"],
                                alert["qn"],
                                index,
                                attempt,
                            )
                        else:
                            raise Exception(
                                "No ack received from meshtastic within the timeout"
                            )

                        break
                    except Exception as e:
                        logger.error(
                            "\t [%s][%d][%d] failed on attempt %d with error: %s",
                            alert["fingerprint"],
                            alert["qn"],
                            index,
                            attempt,
                            e,
                        )
                        if attempt == self.connection.maxsendingattempts - 1:
                            raise

        except Exception as e:
            logger.error(
                "\t [%s][%d] send Attempt failed with error: %s",
                alert["fingerprint"],
                alert["qn"],
                e,
            )

    def splitmessagesifnessecary(self, message, alert):
        chunk_size = 160
        if len(message) > chunk_size:
            logger.debug(
                "\t [%s][%d] Message to big, split to chunks",
                alert["fingerprint"],
                alert["qn"],
            )
            chunks = [
                message[i : i + chunk_size]
                for i in range(0, len(message), chunk_size)
            ]
            return chunks
        else:
            logger.debug(
                "\t [%s][%d] Message size okay",
                alert["fingerprint"],
                alert["qn"],
            )
            return [message]

    def formatalert(self, alert: dict):
        message = (
            "Status: "
            + alert["status"]
            + "\n"
            + "In: "
            + alert["inputtime"]
            + "\n"
        )
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
        # if 'description' in alert['annotations']:
        #     message += (
        #         "Description: " + alert['annotations']['description'] + "\n"
        #     )
        if alert["status"] == "resolved":
            correctdate = parser.parse(alert["endsAt"]) + timedelta(
                hours=self.generalconfig.statustimeshift
            )
            message += "Resolved: " + correctdate.strftime("%Y-%m-%d %H:%M:%S")
        elif alert["status"] == "firing":
            correctdate = parser.parse(alert["startsAt"]) + timedelta(
                hours=self.generalconfig.statustimeshift
            )
            message += "Started: " + correctdate.strftime("%Y-%m-%d %H:%M:%S")
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

    def announce(self, alert: dict) -> None:
        """Announce a message."""
        logger.debug('%s> %s', alert)


def create_announcer(
    config: MeshtasticConfig, generalconfig: GeneralConfig
) -> Announcer:
    """Create an announcer."""
    if config.connection is None:
        logger.info(
            '\t No MESHTASTIC connection specified; will write to STDOUT instead.'
        )
        return DummyAnnouncer()

    return MeshtasticAnnouncer(
        config.connection,
        generalconfig,
    )
