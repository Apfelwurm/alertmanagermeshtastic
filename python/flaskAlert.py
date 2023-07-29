import meshtastic, meshtastic.serial_interface
import json, logging, os
from dateutil import parser
from flask import Flask
from flask import request
from flask_basicauth import BasicAuth
import queue
import threading

app = Flask(__name__)
app.secret_key = "changeKeyHeere"
basic_auth = BasicAuth(app)

nodeID = int(os.getenv("nodeID"))
max_sending_attempts = int(os.getenv("maxsendingattempts"))
app.config["BASIC_AUTH_FORCE"] = os.getenv("auth")
app.config["BASIC_AUTH_USERNAME"] = os.getenv("username")
app.config["BASIC_AUTH_PASSWORD"] = os.getenv("password")

# Create a single-threaded queue
data_queue = queue.Queue()


# Worker function that processes the queue
def process_queue():
    while True:
        try:
            alert = data_queue.get()
            try:
                app.logger.debug("\t queue working on %s", alert["fingerprint"])

                app.logger.debug(
                    "\t========================================================================================================"
                )
                app.logger.debug("\tprocessing alert")
                app.logger.debug("\t %s", alert)
                app.logger.debug(
                    "\t========================================================================================================"
                )
                message = formatalert(alert)
                app.logger.debug(
                    "\t========================================================================================================"
                )
                app.logger.debug("\tFull message:")
                app.logger.debug("\t%s", message)
                app.logger.debug(
                    "\t========================================================================================================"
                )

            except Exception as e:
                app.logger.error(
                    "\t Message failed: %s",
                    e,
                )
                raise

            try:
                chunks = splitmessagesifnessecary(message)

            except Exception as e:
                app.logger.error(
                    "\t could not split in chunks: %s",
                    e,
                )
                raise

            for chunk in chunks:
                for attempt in range(max_sending_attempts):
                    app.logger.debug("\sending chunk attempt %d :%s ", attempt, chunk)
                    try:
                        interface = meshtastic.serial_interface.SerialInterface(
                            os.getenv("meshtty")
                        )
                        interface.sendText(
                            chunk,
                            nodeID,
                            True,
                            False,
                            interface.getNode(nodeID, False).onAckNak,
                        )
                        interface.waitForAckNak()
                        app.logger.debug("\sending chunk attempt %d success ", attempt)
                        break
                    except Exception as e:
                        app.logger.error(
                            "\t chunk Attempt %d failed with error: %s",
                            attempt + 1,
                            e,
                        )
                        if attempt == max_sending_attempts - 1:
                            raise
                    finally:
                        interface.close()
            data_queue.task_done()
        except queue.Empty:
            break


# Thread to run the worker function
worker_thread = threading.Thread(target=process_queue)
worker_thread.daemon = True
worker_thread.start()


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
    chunk_size = 199
    if len(message) > chunk_size:
        app.logger.debug("\tMessage to big, split to chunks")
        chunks = [
            message[i : i + chunk_size] for i in range(0, len(message), chunk_size)
        ]
        return chunks
    else:
        app.logger.debug("\tMessage size okay")
        return [message]
    

def formatalert(alert):
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



@app.route("/alert", methods=["POST"])
def postalertmanager():
    try:
        content = json.loads(request.get_data())
        for alert in content["alerts"]:
            app.logger.debug("\t put in queue: %s", alert["fingerprint"])
            data_queue.put(alert)

        return "Alert OK", 200
    except Exception as error:
        app.logger.error(
            "\t could not queue alerts: %s ",
            error,
        )
        return "Alert fail", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9119)
