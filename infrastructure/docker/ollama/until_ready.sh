#!/bin/bash
# until_ready.sh: Waits for a specified host:port to be ready.

HOST="localhost"
PORT=${1:-80} # Default to port 80 if not provided
shift || true

echo "Waiting for $HOST:$PORT to be ready..."

# Wait for the service to be available
while ! nc -z $HOST $PORT; do
  echo "Service at $HOST:$PORT not yet available. Waiting..."
  sleep 2
done

echo "Service at $HOST:$PORT is ready."