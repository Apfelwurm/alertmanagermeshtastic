#!/bin/bash

if [ "x" == "x$username" ]; then
  echo "warning: username is not set"
else
  echo "admin user is $username"
fi

if [ "x" == "x$password" ]; then
  echo "warning: password is not set"
else
  echo "password is set (not visible)"
fi

sed -i s/XXXUSERNAME/"$username"/ flaskAlert.py
sed -i s/XXXPASSWORD/"$password"/ flaskAlert.py

/usr/bin/gunicorn -w 4 -b 0.0.0.0:9119 flaskAlert:app
