#!/bin/bash
set +e

# Extract IP address from SOCAT_CONNECTION environment variable
IP=$(echo $SOCAT_CONNECTION | awk -F '[[:alpha:]]*:' '{print $2}' | awk -F ':' '{print $1}')

# Check if IP extraction was successful
if [ -z "$IP" ]; then
  echo "Failed to extract IP address from SOCAT_CONNECTION."
  exit 1
fi

echo "Pinging IP address: $IP"

# Initialize failure counter
fail_count=0

# Function to kill all socat processes
kill_socat_processes() {
  socat_pids=$(pidof socat)
  echo "found pids $socat_pids"
  if [ -n "$socat_pids" ]; then
    echo "kill pids $socat_pids"
    kill -9 $socat_pids
  else
    echo "No socat processes found to kill."
  fi
}

# Ping the IP address
while true; do
  if ping -c 1 $IP &> /dev/null; then
    fail_count=0  # Reset failure counter on successful ping
  else
    echo "Error: Ping to $IP failed"
    ((fail_count++))
  fi

  # Check if ping failed 5 times in a row
  if [ $fail_count -ge 5 ]; then
    echo "Ping failed 5 times in a row. Killing all socat instances."
    kill_socat_processes
    fail_count=0  # Reset failure counter after killing socat
  fi

  # Wait for a while before next ping
  sleep 1
done
