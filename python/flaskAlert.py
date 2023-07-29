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
            interface = meshtastic.serial_interface.SerialInterface(os.getenv("meshtty"))
            alert = data_queue.get()          
            app.logger.debug("\t %s", alert["fingerprint"])
            interface.sendText(
                            alert["fingerprint"],
                            nodeID,
                            True,
                            False,
                            interface.getNode(nodeID, False).onAckNak,
                        )
            interface.waitForAckNak()
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


# def splitmessagesifnessecary(message):
    
#     chunk_size = 199
#     if len(message) > chunk_size:
#         app.logger.debug("\tMessage to big, split to chunks")
#         chunks = [message[i : i + chunk_size] for i in range(0, len(message), chunk_size)]
#         return chunks
#     else:
#         app.logger.debug("\tMessage size okay")
#         return [message]


@app.route("/alert", methods=["POST"])
def postalertmanager():
    try:
        content = json.loads(request.get_data())
        for alert in content["alerts"]:
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
