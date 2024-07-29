# Alertmanager webhook for meshtastic

[![linux/amd64](https://github.com/Apfelwurm/alertmanagermeshtastic/actions/workflows/build-linux-image.yml/badge.svg)](https://github.com/Apfelwurm/alertmanagermeshtastic/actions/workflows/build-linux-image.yml)
[![dockerhub](https://img.shields.io/badge/dockerhub-images-important.svg?logo=Docker)](https://hub.docker.com/r/apfelwurm/alertmanagermeshtastic)
[![github](https://img.shields.io/badge/github-repository-important.svg?logo=Github)](https://github.com/Apfelwurm/alertmanagermeshtastic)
[![pypi](https://img.shields.io/badge/pypi-package-important.svg?logo=Pypi)](https://pypi.org/project/alertmanagermeshtastic)


This little Adapter receives alertmanager webhooks and sends the notifications via a over serial attached Meshtastic device to the specified nodeID.

> **Warning**
> Caution: The Tests that are provided for the code in this repository are not currently updated! Also this is a quickly hacked together peace of software, that has not built any security in it at the moment. If you have the skill and the time to contribute in any way, take a look at the [Contribution section](#contribution)

## Credits
This is based on the work of https://github.com/homeworkprod/weitersager
Thanks to [GUVWAF](https://github.com/GUVWAF) for the support and thanks to the whole meshtastic team for this awsome software!

##  Alertmanager configuration example

```
	receivers:
	- name: 'meshtastic-webhook'
	  webhook_configs:
	  - url: http://alertmanager-meshtastic:9119/alert
	    send_resolved: true
```

## config.toml example

This is an example config, that shows all of the config options.

```
log_level = "debug"

[general]
inputtimeshift = 2      # this time in hours will be added to the "in" time of the message that gets sent to the client
statustimeshift = 2     # this time in hours will be added to the "status" time of the message (startsAt/endsAt) that gets sent to the client

[http]
host = "0.0.0.0"
port = 9119
clearsecret = "your_secret_key"

[meshtastic.connection]
tty = "/tmp/vcom0"
nodeid = 631724152
maxsendingattempts = 30
timeout = 60
```


##  docker compose service example - Hardware Serial (default)

To integrate this bridge into your composed prometheus/alertmanager cluster, this is a good startingpoint.

```
    alertmanagermeshtastic:
      image: apfelwurm/alertmanagermeshtastic
      ports:
        - 9119:9119
      devices:
        -/dev/ttyACM0
      volumes:
        - ./alertmanager-meshtastic/config.toml:/app/config.toml
      restart: always
```

##  docker compose service example - Virtual Serial

To integrate this bridge into your composed prometheus/alertmanager cluster, this is a good startingpoint.
If you plan to use a virtual serial port that is provided with socat you have to use the socat connector in this container or run your alertmanagermeshtastic instance on the terminating linux machine, because the reconnecting is not working if you either mount it as volume or as a device.

```
    alertmanagermeshtastic:
      image: apfelwurm/alertmanagermeshtastic
      ports:
        - 9119:9119
      environment:
        - SOCAT_ENABLE=TRUE
        - SOCAT_CONNECTION=tcp:192.168.178.46:5000
      volumes:
        - ./alertmanager-meshtastic/config.toml:/app/config.toml
      restart: always
```

Note: If you set SOCAT_ENABLE to TRUE, the tty option from [meshtastic.connection] in config.toml will be overwritten with /tmp/vcom0 as thats the virtual serial port.

##  Running on docker example - Hardware Serial (default)

```
    docker run -d --name alertmanagermeshtastic \
		--device=/dev/ttyACM0 \
		-v ./alertmanager-meshtastic/config.toml:/app/config.toml \
    -p 9119:9119 apfelwurm/alertmanagermeshtastic:latest
```

##  Running on docker example - Virtual Serial

If you plan to use a virtual serial port that is provided with socat you have to use the socat connector in this container or run your alertmanagermeshtastic instance on the terminating linux machine, because the reconnecting is not working if you either mount it as volume or as a device.

```
    docker run -d --name alertmanagermeshtastic \
		--env SOCAT_ENABLE=TRUE --env SOCAT_CONNECTION=tcp:192.168.178.46:5000 \
		-v ./alertmanager-meshtastic/config.toml:/app/config.toml \
    -p 9119:9119 apfelwurm/alertmanagermeshtastic:latest
```
Note: If you set SOCAT_ENABLE to TRUE, the tty option from [meshtastic.connection] in config.toml will be overwritten with /tmp/vcom0 as thats the virtual serial port.


## Metrics for Prometheus
You cann add this as an exporter to your scrape config, for example:

```
scrape_configs:
  - job_name: "alertmanager-meshtastic"
    scrape_interval: 10s
    static_configs:
      - targets: ["alertmanager-meshtastic:9119"]
```

it will return the metrics

`message_queue_size` (int/gauge)
`meshtastic_connected` (bool/gauge)

## Contribution

This is currently a minimal implementation that supports only a single node as a receiver. If you need additional features, you are welcome to open an issue, or even better, submit a pull request. You can also take a look on the opened Issues, where i have opened some for planned features and work on them if you want. I would appreciate any help.


## Example to test

You can use the test.sh or the test single.sh or the following curl command to test alertmanager-meshtastic
```
	curl -XPOST --data '{"status":"resolved","groupLabels":{"alertname":"instance_down"},"commonAnnotations":{"description":"i-0d7188fkl90bac100 of job ec2-sp-node_exporter has been down for more than 2 minutes.","summary":"Instance i-0d7188fkl90bac100 down"},"alerts":[{"status":"resolved","labels":{"name":"olokinho01-prod","instance":"i-0d7188fkl90bac100","job":"ec2-sp-node_exporter","alertname":"instance_down","os":"linux","severity":"page"},"endsAt":"2019-07-01T16:16:19.376244942-03:00","generatorURL":"http://pmts.io:9090","startsAt":"2019-07-01T16:02:19.376245319-03:00","annotations":{"description":"i-0d7188fkl90bac100 of job ec2-sp-node_exporter has been down for more than 2 minutes.","summary":"Instance i-0d7188fkl90bac100 down"}}],"version":"4","receiver":"infra-alert","externalURL":"http://alm.io:9093","commonLabels":{"name":"olokinho01-prod","instance":"i-0d7188fkl90bac100","job":"ec2-sp-node_exporter","alertname":"instance_down","os":"linux","severity":"page"}}' http://alertmanager-meshtastic:9119/alert
```
