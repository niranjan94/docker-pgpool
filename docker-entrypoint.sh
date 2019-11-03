#!/bin/bash

if [[ -f "/opt/initialized" ]]; then
  echo "Initialized."
else
  ./initialize
  touch /opt/initialized
fi

if [[ -f "/var/run/pgpool/pgpool.pid" ]]; then
  rm -f /var/run/pgpool/pgpool.pid
  fuser -k 9999/tcp 9000/tcp
fi

exec "$@"
