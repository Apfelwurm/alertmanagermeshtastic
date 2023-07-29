import meshtastic, meshtastic.serial_interface
from meshtastic import mesh_pb2
import json, logging, os
from dateutil import parser
from flask import Flask
from flask import request
from flask_basicauth import BasicAuth

app = Flask(__name__)
app.secret_key = "changeKeyHeere"
basic_auth = BasicAuth(app)

nodeID = int(os.getenv("nodeID"))
max_sending_attempts = int(os.getenv("maxsendingattempts"))
max_chunk_sending_attempts = int(os.getenv("maxchunksendingattempts"))
app.config["BASIC_AUTH_FORCE"] = os.getenv("auth")
app.config["BASIC_AUTH_USERNAME"] = os.getenv("username")
app.config["BASIC_AUTH_PASSWORD"] = os.getenv("password")

interface = meshtastic.serial_interface.SerialInterface(os.getenv("meshtty"))


with app.app_context():
    if os.getenv("loglevel") == "DEBUG":
        app.logger.setLevel(logging.DEBUG)
    if os.getenv("loglevel") == "WARNING":
        app.logger.setLevel(logging.WARNING)
    if os.getenv("loglevel") == "CRITICAL":
        app.logger.setLevel(logging.CRITICAL)
    if os.getenv("loglevel") == "ERROR":
        app.logger.setLevel(logging.ERROR)
    if os.getenv("loglevel") == "INFO":
        app.logger.setLevel(logging.INFO)


def splitmessagesifnessecary(message):
    chunk_size = mesh_pb2.Constants.DATA_PAYLOAD_LEN
    if getattr(message, "SerializeToString", None):
        data = message.SerializeToString()
    else:
        data = message

    if len(data) > chunk_size:
        app.logger.debug("\tMessage to big, split to chunks", message)
        chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
        return chunks
    else:
        app.logger.debug("\tMessage size okay", message)
        return [data]


@app.route("/alert", methods=["POST"])
def postalertmanager():
    try:
        # define the serial interface
        # get content
        content = json.loads(request.get_data())
        for alert in content["alerts"]:
            for attempt in range(max_sending_attempts):
                try:
                    message = "Status: " + alert["status"] + "\n"
                    if "name" in alert["labels"]:
                        message += (
                            "Instance: "
                            + alert["labels"]["instance"]
                            + "("
                            + alert["labels"]["name"]
                            + ")\n"
                        )
                    else:
                        message += "Instance: " + alert["labels"]["instance"] + "\n"
                    if "info" in alert["annotations"]:
                        message += "Info: " + alert["annotations"]["info"] + "\n"
                    if "summary" in alert["annotations"]:
                        message += "Summary: " + alert["annotations"]["summary"] + "\n"
                    if "description" in alert["annotations"]:
                        message += (
                            "Description: " + alert["annotations"]["description"] + "\n"
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
                    app.logger.debug("\tMessage:%s", message)

                    chunks = splitmessagesifnessecary(message)
                    for chunk in chunks:
                        for cattempt in range(max_chunk_sending_attempts):
                            try:
                                interface.sendText(
                                    chunk,
                                    nodeID,
                                    True,
                                    False,
                                    interface.getNode(nodeID, False).onAckNak,
                                )
                                interface.waitForAckNak()
                                break
                            except Exception as e:
                                app.logger.error(
                                    "\t chunk Attempt %d failed with error: %s",
                                    cattempt + 1,
                                    e,
                                )
                                if (
                                    cattempt == max_chunk_sending_attempts - 1
                                ):  # If this was the last attempt
                                    raise  # Re-raise the last exception

                    break  # If the code above succeeds, break the loop
                except Exception as e:
                    app.logger.error(
                        "\t Attempt %d failed with error: %s", attempt + 1, e
                    )
                    if (
                        attempt == max_sending_attempts - 1
                    ):  # If this was the last attempt
                        raise  # Re-raise the last exception
        return "Alert OK", 200
    except Exception as error:
        app.logger.error(
            "\tAt least one alert could not be delivered after %d attempts, the error is: %s ",
            max_sending_attempts,
            error,
        )
        return "Alert fail", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9119)
