#!/bin/bash


# Load environment variables from .env if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Restart up to 5 times on abnormal exit
MAX_RETRIES=5
COUNT=0
while [ $COUNT -lt $MAX_RETRIES ]; do
    python3 -m bot.main
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        break
    fi
    COUNT=$((COUNT+1))
    echo "Bot exited abnormally (exit code $EXIT_CODE). Restarting ($COUNT/$MAX_RETRIES)..."
    sleep 2
done
if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "Bot failed $MAX_RETRIES times. Exiting."
    exit 1
fi
