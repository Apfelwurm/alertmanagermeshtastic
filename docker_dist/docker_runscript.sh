#!/bin/bash
if [[ $SOCAT_ENABLE == "" ]]; then
    export SOCAT_ENABLE=FALSE
fi

if [[ $SOCAT_ENABLE == TRUE ]]; then

    if [[ $SOCAT_CONNECTION == "" ]]; then
        echo "SOCAT_ENABLE is TRUE but SOCAT_CONNECTION is empty! Please either disable SOCAT_ENABLE or set SOCAT_CONNECTION"
        exit 100
    fi

    cp -f /app/supervisord_socat.conf /etc/supervisor/conf.d/supervisord.conf

    toml set --toml-path /app/config.toml meshtastic.connection.tty "/tmp/vcom0"
else
    cp -f /app/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
fi

/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
