import meshtastic, meshtastic.serial_interface
import json, logging, os
from dateutil import parser
from flask import Flask
from flask import request
from flask_basicauth import BasicAuth
from pubsub import pub

app = Flask(__name__)
app.secret_key = 'changeKeyHeere'
basic_auth = BasicAuth(app)

# # Yes need to have -, change it!
nodeID = int(os.getenv('nodeID'))

# Authentication conf, change it!
app.config['BASIC_AUTH_FORCE'] = os.getenv('auth')
app.config['BASIC_AUTH_USERNAME'] = os.getenv('username')
app.config['BASIC_AUTH_PASSWORD'] = os.getenv('password')

def onreceive(packet, interface):  # pylint: disable=unused-argument
    """called when a packet arrives"""
    print(f"Received: {packet}")
    try:
        interface.getNode(nodeID, False).iface.waitForAckNak()
        print(f"ack")
    except Exception as error:
        app.logger.error("\trecverror: %s",error)


pub.subscribe(onreceive, "meshtastic.receive")


@app.route('/alert', methods = ['POST'])
def postalertmanager():

    try:
        # define the serial interface
        interface =  meshtastic.serial_interface.SerialInterface()
        # get content
        content = json.loads(request.get_data())
        for alert in content['alerts']:
            message = "Status: "+alert['status']+"\n"
            if 'name' in alert['labels']:
                message += "Instance: "+alert['labels']['instance']+"("+alert['labels']['name']+")\n"
            else:
                message += "Instance: "+alert['labels']['instance']+"\n"
            if 'info' in alert['annotations']:
                message += "Info: "+alert['annotations']['info']+"\n"
            if 'summary' in alert['annotations']:
                message += "Summary: "+alert['annotations']['summary']+"\n"                
            # if 'description' in alert['annotations']:
            #     message += "Description: "+alert['annotations']['description']+"\n"
            if alert['status'] == "resolved":
                correctDate = parser.parse(alert['endsAt']).strftime('%Y-%m-%d %H:%M:%S')
                message += "Resolved: "+correctDate
            elif alert['status'] == "firing":
                correctDate = parser.parse(alert['startsAt']).strftime('%Y-%m-%d %H:%M:%S')
                message += "Started: "+correctDate
            app.logger.info("\t%s",message)
            interface.sendText(message, nodeID)
            interface.sendText(message, nodeID, True)
            return "Alert OK", 200
    except Exception as error:
        app.logger.error("\t%s",error)
        return "Alert fail", 200
    finally:
        interface.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=9119)
