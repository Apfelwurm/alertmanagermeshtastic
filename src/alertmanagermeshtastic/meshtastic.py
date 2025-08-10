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


class MeshtasticTimeoutError(Exception):
    """Raised when a meshtastic acknowledgment times out."""

    pass


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
            except Exception as e:  # noqa: BLE001
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
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "\t Connnection to meshtastic failed with error: %s , retry in 2 seconds",
                    e,
                )
                time.sleep(2)

    def start(self) -> None:
        """Connect to the connection, in a separate thread."""
        nodeids_str = ", ".join(str(nid) for nid in self.connection.nodeids)
        logger.info(
            '\t Connecting to MESHTASTIC connection %s, the nodes are [%s] and messages will be sent %d times with timeout %d before failing',
            self.connection.tty,
            nodeids_str,
            self.connection.maxsendingattempts,
            self.connection.timeout,
        )
        pub.subscribe(self._onconnect, "meshtastic.connection.established")
        # start_thread(self.meshtasticinterface.start)

    def announce(self, alert: dict) -> None:
        """Announce a message to all configured nodes sequentially."""
        # Note: This is called by the old interface or when announce_to_node isn't available
        # The new approach processes nodes one by one at the processor level
        for nodeid in self.connection.nodeids:
            try:
                self.announce_to_node(alert, nodeid)
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "\t [%s][%d][node:%d] Failed to send to node: %s",
                    alert["fingerprint"],
                    alert["qn"],
                    nodeid,
                    e,
                )
                # Continue to next node instead of failing entirely
                continue

    # ---------------- Internal helpers for sending/acks -----------------
    def _send_chunk_with_ack(
        self, nodeid: int, header: str, payload: str, attempt: int, index: int
    ) -> None:
        """Send one chunk and wait ONLY for an explicit remote ACK.

        We intentionally IGNORE implicit ACKs (receivedImplAck) because they only
        confirm local transmission, not reception by the destination node. This
        prevents false positives when the target node is powered off or unreachable.
        """
        # Reset ack flags before send
        try:
            self.meshtasticinterface._acknowledgment.reset()  # noqa: SLF001
        except Exception:  # noqa: BLE001
            pass

        # Use the node's onAckNak handler so acknowledgment flags get set correctly
        node = self.meshtasticinterface.getNode(nodeid, False)
        text = f"{header}\n{payload}"
        self.meshtasticinterface.sendText(
            text=text,
            destinationId=nodeid,
            wantAck=True,
            wantResponse=False,
            onResponse=node.onAckNak,
        )

        a = self.meshtasticinterface._acknowledgment  # noqa: SLF001
        start_time = time.time()
        saw_impl = False
        while True:
            elapsed = time.time() - start_time
            if a.receivedAck:
                logger.debug(
                    "\t [node:%d][idx:%d] explicit ACK after %.2fs (attempt %d)",
                    nodeid,
                    index,
                    elapsed,
                    attempt,
                )
                break
            if a.receivedNak:
                logger.debug(
                    "\t [node:%d][idx:%d] NAK after %.2fs (attempt %d)",
                    nodeid,
                    index,
                    elapsed,
                    attempt,
                )
                raise MeshtasticTimeoutError("Received NAK from node")
            if a.receivedImplAck and not saw_impl:
                saw_impl = True
                logger.debug(
                    "\t [node:%d][idx:%d] implicit ACK observed (still waiting for explicit) attempt %d",
                    nodeid,
                    index,
                    attempt,
                )
            if elapsed >= self.connection.timeout:
                # Timeout without explicit ack
                if saw_impl:
                    logger.debug(
                        "\t [node:%d][idx:%d] timeout after implicit ACK only (no explicit received)",
                        nodeid,
                        index,
                    )
                raise MeshtasticTimeoutError(
                    "No explicit ACK received within timeout"
                )
            time.sleep(0.25)
        # reset after handling
        try:
            a.reset()
        except Exception:  # noqa: BLE001
            pass

    def _send_chunks(self, alert: dict, nodeid: int, chunks: list[str]) -> None:
        total = len(chunks)
        for index, chunk in enumerate(chunks):
            header = f"{alert['qn']}:{index + 1}/{total}"
            success = False
            for attempt in range(self.connection.maxsendingattempts):
                logger.debug(
                    "\t [%s][%d][node:%d][%d/%d] attempt %d",
                    alert["fingerprint"],
                    alert["qn"],
                    nodeid,
                    index + 1,
                    total,
                    attempt,
                )
                try:
                    self._send_chunk_with_ack(
                        nodeid, header, chunk, attempt, index
                    )
                    success = True
                    break
                except Exception as e:  # noqa: BLE001
                    logger.error(
                        "\t [%s][%d][%d][%d] failed attempt %d: %s",
                        alert["fingerprint"],
                        alert["qn"],
                        nodeid,
                        index,
                        attempt,
                        e,
                    )
                    if attempt == self.connection.maxsendingattempts - 1:
                        raise
                    time.sleep(1)
            if not success:
                raise MeshtasticTimeoutError(
                    f"Chunk {index + 1}/{total} to node {nodeid} failed"
                )

    # ---------------- Public per-node send -----------------
    def announce_to_node(self, alert: dict, nodeid: int) -> None:
        try:
            message = self.formatalert(alert)
            chunks = self.splitmessagesifnessecary(message, alert)
            logger.debug(
                "\t [%s][%d][node:%d] %d chunk(s) prepared",
                alert["fingerprint"],
                alert["qn"],
                nodeid,
                len(chunks),
            )
            self._send_chunks(alert, nodeid, chunks)
        except Exception as e:  # noqa: BLE001
            logger.error(
                "\t [%s][%d][node:%d] send Attempt failed: %s",
                alert["fingerprint"],
                alert["qn"],
                nodeid,
                e,
            )
            raise

    def splitmessagesifnessecary(self, message, alert):
        chunk_size = 160
        if len(message) > chunk_size:
            logger.debug(
                "\t [%s][%d] Message to big, split to chunks",
                alert["fingerprint"],
                alert["qn"],
            )
            return [
                message[i : i + chunk_size]
                for i in range(0, len(message), chunk_size)
            ]
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

    while True:
        try:
            logger.info("Creating interface...")
            meshtasticinterface = Meshtasticinterface(connection.tty)
            logger.info("interface recreated!")
            break
        except Exception as e:  # noqa: BLE001
            logger.error(
                "\t Connnection to meshtastic failed with error: %s , retry in 2 seconds",
                e,
            )
            time.sleep(2)

    return meshtasticinterface


class DummyAnnouncer(Announcer):
    """An announcer that writes messages to STDOUT."""

    def announce(self, alert: dict) -> None:
        """Announce a message."""
        logger.debug('Alert: %s', alert)


def create_announcer(
    config: MeshtasticConfig, generalconfig: GeneralConfig
) -> Announcer:
    """Create an announcer."""
    if config.connection is None or not config.connection.tty:
        logger.info(
            '\t No MESHTASTIC connection specified; will write to STDOUT instead.'
        )
        return DummyAnnouncer()

    return MeshtasticAnnouncer(
        config.connection,
        generalconfig,
    )
