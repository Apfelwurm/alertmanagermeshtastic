# Alertmanager webhook for meshtastic (Python Version)

[![linux/amd64](https://github.com/Apfelwurm/alertmanager-webhook-meshtastic-python/actions/workflows/build-linux-image.yml/badge.svg)](https://github.com/Apfelwurm/alertmanager-webhook-meshtastic-python/actions/workflows/build-linux-image.yml)

based on the work of https://github.com/nopp/alertmanager-webhook-telegram-python
Python version 3

## INSTALL

* pip install -r requirements.txt

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
    docker run -d --name alertmanager-webhook-meshtastic-python \
		--device=/dev/ttyACM0 \
    	-e "nodeID=123456789" \
    	-e "auth=true" \
    	-e "username=XXXUSERNAME" \
    	-e "password=XXXPASSWORD" \
    	-p 9119:9119 apfelwurm/alertmanager-webhook-meshtastic-python:latest

Example to test
===============
	curl -XPOST --data '{"status":"resolved","groupLabels":{"alertname":"instance_down"},"commonAnnotations":{"description":"i-0d7188fkl90bac100 of job ec2-sp-node_exporter has been down for more than 2 minutes.","summary":"Instance i-0d7188fkl90bac100 down"},"alerts":[{"status":"resolved","labels":{"name":"olokinho01-prod","instance":"i-0d7188fkl90bac100","job":"ec2-sp-node_exporter","alertname":"instance_down","os":"linux","severity":"page"},"endsAt":"2019-07-01T16:16:19.376244942-03:00","generatorURL":"http://pmts.io:9090","startsAt":"2019-07-01T16:02:19.376245319-03:00","annotations":{"description":"i-0d7188fkl90bac100 of job ec2-sp-node_exporter has been down for more than 2 minutes.","summary":"Instance i-0d7188fkl90bac100 down"}}],"version":"4","receiver":"infra-alert","externalURL":"http://alm.io:9093","commonLabels":{"name":"olokinho01-prod","instance":"i-0d7188fkl90bac100","job":"ec2-sp-node_exporter","alertname":"instance_down","os":"linux","severity":"page"}}' http://XXXUSERNAME:XXXPASSWORD@flaskAlert:9119/alert
