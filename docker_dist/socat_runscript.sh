#!/bin/bash
set +e

while true
do
   socat pty,link=/tmp/vcom0,raw,group-late=dialout,mode=660 $SOCAT_CONNECTION
   sleep 2
done