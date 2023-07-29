import meshtastic, meshtastic.serial_interface
import json, logging, os
from dateutil import parser
from flask import Flask
from flask import request
from flask_basicauth import BasicAuth

app = Flask(__name__)
app.secret_key = 'changeKeyHeere'
basic_auth = BasicAuth(app)

nodeID = int(os.getenv('nodeID'))

app.config['BASIC_AUTH_FORCE'] = os.getenv('auth')
app.config['BASIC_AUTH_USERNAME'] = os.getenv('username')
app.config['BASIC_AUTH_PASSWORD'] = os.getenv('password')

interface =  meshtastic.serial_interface.SerialInterface(os.getenv('meshtty'))


with app.app_context():
    if os.getenv('loglevel') == "DEBUG":
        app.logger.setLevel(logging.DEBUG)
    if os.getenv('loglevel') == "WARNING":
        app.logger.setLevel(logging.WARNING)
    if os.getenv('loglevel') == "CRITICAL":
        app.logger.setLevel(logging.CRITICAL)
    if os.getenv('loglevel') == "ERROR":
        app.logger.setLevel(logging.ERROR)
    if os.getenv('loglevel') == "INFO":
        app.logger.setLevel(logging.INFO)



@app.route('/alert', methods = ['POST'])
def postalertmanager():

    try:
        # define the serial interface
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
            if 'description' in alert['annotations']:
                message += "Description: "+alert['annotations']['description']+"\n"
            if alert['status'] == "resolved":
                correctDate = parser.parse(alert['endsAt']).strftime('%Y-%m-%d %H:%M:%S')
                message += "Resolved: "+correctDate
            elif alert['status'] == "firing":
                correctDate = parser.parse(alert['startsAt']).strftime('%Y-%m-%d %H:%M:%S')
                message += "Started: "+correctDate
            app.logger.debug("\tMessage:%s", message)
            interface.sendText(message, nodeID, True,False,interface.getNode(nodeID, False).onAckNak)
            interface.waitForAckNak()
            return "Alert OK", 200
    except Exception as error:
        app.logger.error("\t%s",error)
        return "Alert fail", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9119)