#!/bin/bash

# Kill any existing ngrok processes to avoid conflicts
pkill -f ngrok

# Navigate to backend directory but do not start Django server yet
cd backend

# Read SERVER_URL from .env file, ignoring lines that are commented out
while IFS='=' read -r key value
do
  if [[ $key != \#* ]]; then
    eval ${key}=$(echo ${value} | sed 's|https://||')
  fi
done < <(grep 'SERVER_URL' .env)

echo "SERVER_URL: ${SERVER_URL}"

# Start ngrok with the dynamic server URL and silence its output
ngrok http --domain="${SERVER_URL}" 8080 
