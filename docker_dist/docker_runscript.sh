if [[ $SOCAT_ENABLE == "" ]]; then
    export SOCAT_ENABLE=FALSE
fi

if [[ $SOCAT_ENABLE == TRUE ]]; then

    if [[ $SOCAT_CONNECTION == "" ]]; then
        echo "SOCAT_ENABLE is TRUE but SOCAT_CONNECTION is empty! Please either disable SOCAT_ENABLE or set SOCAT_CONNECTION"
        exit 100
    fi

    sed -i "s|%%SOCAT_CONNECTION%%|$SOCAT_CONNECTION|g" /app/supervisord_socat.conf
    cat /app/supervisord_socat.conf >>/etc/supervisor/conf.d/supervisord.conf

    toml set --toml-path /app/config.toml meshtastic.connection.tty "/tmp/vcom0"
fi

/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
