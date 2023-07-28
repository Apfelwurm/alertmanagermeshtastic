FROM alpine:3.18

LABEL maintainer="Alexander Volz <Alexander@volzit.de>"

WORKDIR /alertmanager-webhook-meshtastic
RUN adduser -D meshtastic && addgroup meshtastic dialout
RUN apk update \
                && apk add py3-pip bash gcc python3-dev musl-dev libffi-dev openssl-dev unzip \
                && rm -rf /var/cache/apk/* 
COPY --chown=meshtastic:meshtastic /python/* /alertmanager-webhook-meshtastic/
COPY --chown=meshtastic:meshtastic /docker/run.sh /alertmanager-webhook-meshtastic/run.sh

RUN pip install -r requirements.txt
RUN chmod +x run.sh

EXPOSE 9119
USER meshtastic

ENTRYPOINT ["./run.sh"]
