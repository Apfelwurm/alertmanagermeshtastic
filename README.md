# Alertmanager webhook for meshtastic (Python Version)

![Docker Image CI](https://github.com/apfelwurm/alertmanager-webhook-meshtastic-python/workflows/Docker%20Image%20CI/badge.svg)
![Code scanning - action](https://github.com/apfelwurm/alertmanager-webhook-meshtastic-python/workflows/Code%20scanning%20-%20action/badge.svg)

based on the work of https://github.com/nopp/alertmanager-webhook-telegram-python
Python version 3

## INSTALL

* pip install -r requirements.txt

Change on flaskAlert.py
=======================
If you'll use with authentication, change too

* XXXUSERNAME
* XXXPASSWORD

Disabling authentication
========================
On flaskAlert.py change app.config['BASIC_AUTH_FORCE'] = True to app.config['BASIC_AUTH_FORCE'] = False

Alertmanager configuration example
==================================

	receivers:
	- name: 'meshtastic-webhook'
	  webhook_configs:
	  - url: http://ipFlaskAlert:9119/alert
	    send_resolved: true
	    http_config:
	      basic_auth:
		username: 'XXXUSERNAME'
		password: 'XXXPASSWORD'

Running
=======
* python flaskAlert.py

Running on docker
=================
    git clone https://github.com/nopp/alertmanager-webhook-telegram.git
    cd alertmanager-webhook-telegram
    docker build -f docker/Dockerfile -t alertmanager-webhook-meshtastic-python:latest .

    docker run -d --name alertmanager-webhook-meshtastic-python \
		--device=/dev/ttyACM0 \
    	-e "username=<username>" \
    	-e "password=<password>" \
    	-p 9119:9119 alertmanager-webhook-meshtastic-python:latest

Example to test
===============
	curl -XPOST --data '{"status":"resolved","groupLabels":{"alertname":"instance_down"},"commonAnnotations":{"description":"i-0d7188fkl90bac100 of job ec2-sp-node_exporter has been down for more than 2 minutes.","summary":"Instance i-0d7188fkl90bac100 down"},"alerts":[{"status":"resolved","labels":{"name":"olokinho01-prod","instance":"i-0d7188fkl90bac100","job":"ec2-sp-node_exporter","alertname":"instance_down","os":"linux","severity":"page"},"endsAt":"2019-07-01T16:16:19.376244942-03:00","generatorURL":"http://pmts.io:9090","startsAt":"2019-07-01T16:02:19.376245319-03:00","annotations":{"description":"i-0d7188fkl90bac100 of job ec2-sp-node_exporter has been down for more than 2 minutes.","summary":"Instance i-0d7188fkl90bac100 down"}}],"version":"4","receiver":"infra-alert","externalURL":"http://alm.io:9093","commonLabels":{"name":"olokinho01-prod","instance":"i-0d7188fkl90bac100","job":"ec2-sp-node_exporter","alertname":"instance_down","os":"linux","severity":"page"}}' http://username:password@flaskAlert:9119/alert
