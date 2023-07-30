# Alertmanager webhook for meshtastic

[![linux/amd64](https://github.com/Apfelwurm/alertmanager-webhook-meshtastic-python/actions/workflows/build-linux-image.yml/badge.svg)](https://github.com/Apfelwurm/alertmanager-webhook-meshtastic-python/actions/workflows/build-linux-image.yml)
[![dockerhub](https://img.shields.io/badge/dockerhub-images-important.svg?logo=Docker)](https://hub.docker.com/r/apfelwurm/alertmanager-webhook-meshtastic-python)
[![github](https://img.shields.io/badge/github-repository-important.svg?logo=Github)](https://github.com/Apfelwurm/alertmanager-webhook-meshtastic-python)


This little Adapter receives alertmanager webhooks and sends the notifications via a over serial attached Meshtastic device to the specified nodeID. (currently not working and docs not updated!)

## Credits
This is based on the work of https://github.com/homeworkprod/weitersager
Thanks to [GUVWAF](https://github.com/GUVWAF) for the support and thanks to the whole meshtastic team for this awsome software!

##  Alertmanager configuration example
	receivers:
	- name: 'meshtastic-webhook'
	  webhook_configs:
	  - url: http://ipFlaskAlert:9119/alert
	    send_resolved: true
	    http_config:
	      basic_auth:
		username: 'XXXUSERNAME'
		password: 'XXXPASSWORD'

##  docker compose service example - Hardware Serial (default)

To integrate this bridge into your composed prometheus/alertmanager cluster, this is a good startingpoint.
If you plan to use a virtual serial port that is provided with socat (for example /tmp/vcom0), you have to use a volume mount instead of the device binding:

```
    alertmanagermeshtastic:
      image: apfelwurm/alertmanager-webhook-meshtastic-python
      ports:
        - 9119:9119
      volumes:
        - /tmp/vcom0:/tmp/vcom0
      environment:
        - meshtty=/tmp/vcom0
        - nodeID=631724152
        - maxsendingattempts=5
        - auth=true
        - username=XXXUSERNAME
        - password=XXXPASSWORD
        - loglevel=WARNING
      restart: always
```

##  docker compose service example - Virtual Serial

To integrate this bridge into your composed prometheus/alertmanager cluster, this is a good startingpoint.
If you plan to use a virtual serial port that is provided with socat (for example /tmp/vcom0), you have to use a volume mount instead of the device binding:

```
    alertmanagermeshtastic:
      image: apfelwurm/alertmanager-webhook-meshtastic-python
      ports:
        - 9119:9119
      volumes:
        - /tmp/vcom0:/tmp/vcom0
      environment:
        - meshtty=/tmp/vcom0
        - nodeID=631724152
        - maxsendingattempts=5
        - auth=true
        - username=XXXUSERNAME
        - password=XXXPASSWORD
        - loglevel=WARNING
      restart: always
```


##  Running on docker example - Hardware Serial (default)

```
    docker run -d --name alertmanager-webhook-meshtastic-python \
		--device=/dev/ttyACM0 \
		-e "meshtty=/dev/ttyACM0" \
      -e "maxsendingattempts=5" \
    	-e "nodeID=123456789" \
    	-e "auth=true" \
    	-e "username=XXXUSERNAME" \
    	-e "password=XXXPASSWORD" \
    	-e "loglevel=WARNING" \
    	-p 9119:9119 apfelwurm/alertmanager-webhook-meshtastic-python:latest
```

##  Running on docker example - Virtual Serial

If you plan to use a virtual serial port that is provided with socat (for example /tmp/vcom0), you have to use a volume mount instead of the device binding:

```
    docker run -d --name alertmanager-webhook-meshtastic-python \
		-v /tmp/vcom0:/tmp/vcom0 \
		-e "meshtty=/tmp/vcom0" \
    	-e "nodeID=123456789" \
      -e "maxsendingattempts=5" \
    	-e "auth=true" \
    	-e "username=XXXUSERNAME" \
    	-e "password=XXXPASSWORD" \
    	-e "loglevel=WARNING" \
    	-p 9119:9119 apfelwurm/alertmanager-webhook-meshtastic-python:latest
```

## Contribution

This is currently a minimal implementation that supports only a single node as a receiver. If you need additional features, you are welcome to open an issue, or even better, submit a pull request. I would appreciate any help.


## Example to test
```
	curl -XPOST --data '{"status":"resolved","groupLabels":{"alertname":"instance_down"},"commonAnnotations":{"description":"i-0d7188fkl90bac100 of job ec2-sp-node_exporter has been down for more than 2 minutes.","summary":"Instance i-0d7188fkl90bac100 down"},"alerts":[{"status":"resolved","labels":{"name":"olokinho01-prod","instance":"i-0d7188fkl90bac100","job":"ec2-sp-node_exporter","alertname":"instance_down","os":"linux","severity":"page"},"endsAt":"2019-07-01T16:16:19.376244942-03:00","generatorURL":"http://pmts.io:9090","startsAt":"2019-07-01T16:02:19.376245319-03:00","annotations":{"description":"i-0d7188fkl90bac100 of job ec2-sp-node_exporter has been down for more than 2 minutes.","summary":"Instance i-0d7188fkl90bac100 down"}}],"version":"4","receiver":"infra-alert","externalURL":"http://alm.io:9093","commonLabels":{"name":"olokinho01-prod","instance":"i-0d7188fkl90bac100","job":"ec2-sp-node_exporter","alertname":"instance_down","os":"linux","severity":"page"}}' http://XXXUSERNAME:XXXPASSWORD@flaskAlert:9119/alert
```