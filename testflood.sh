#!/bin/bash
count=0

while true; do
    ((count++))
    echo $count
    curl -XPOST -H 'Content-Type: application/json' --data "{\"status\":\"resolved\",\"groupLabels\":{\"alertname\":\"instance_down\"},\"commonAnnotations\":{\"description\":\"i-0d7188fkl90bac100 of job ec2-sp-node_exporter has been down for more than 2 minutes.$count\",\"summary\":\"Instance i-$count down\"},\"alerts\":[{\"status\":\"resolved\",\"fingerprint\":\"testfingerprint$count\",\"labels\":{\"name\":\"olokinho01-prod\",\"instance\":\"i-$count\",\"job\":\"ec2-sp-node_exporter\",\"alertname\":\"instance_down\",\"os\":\"linux\",\"severity\":\"page\"},\"endsAt\":\"2019-07-01T16:16:19.376244942-03:00\",\"generatorURL\":\"http://pmts.io:9090\",\"startsAt\":\"2019-07-01T16:02:19.376245319-03:00\",\"annotations\":{\"description\":\"i-0d7188fkl90bac100 of job ec2-sp-node_exporter has been down for more than 2 minutes.$count\",\"summary\":\"Instance i-$count down\"}}],\"version\":\"4\",\"receiver\":\"infra-alert\",\"externalURL\":\"http://alm.io:9093\",\"commonLabels\":{\"name\":\"olokinho01-prod\",\"instance\":\"i-$count\",\"job\":\"ec2-sp-node_exporter\",\"alertname\":\"instance_down\",\"os\":\"linux\",\"severity\":\"page\"}}" http://XXXUSERNAME:XXXPASSWORD@localhost:9119/alert
done
