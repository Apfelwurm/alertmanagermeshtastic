#!/bin/bash

if [ "x" == "x$nodeID" ]; then
  echo "error: nodeID is not set"
  exit 100
else
  echo "nodeID is $nodeID"
fi

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

if [ "x" == "x$auth" ]; then
  echo "warning: auth is not set, disabling auth"
  export auth=false
else
  echo "auth is set to $auth"
fi

if [ "x" == "x$maxsendingattempts" ]; then
  echo "warning: maxsendingattempts is not set, set to default (5)"
  export maxsendingattempts="5"
else
  echo "maxsendingattempts is set to $maxsendingattempts"
fi

/usr/bin/gunicorn -w 1 -b 0.0.0.0:9119 flaskAlert:app
