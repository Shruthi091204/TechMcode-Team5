#!/bin/sh
# testbed/scenarios/bad_config_push.sh
# Injects a broken nginx config into web-01 to simulate a bad deployment

TARGET_CONTAINER="web-01"

echo "Injecting bad configuration into ${TARGET_CONTAINER}..."

# We use 127.0.0.1 to bypass Nginx's strict DNS pre-flight check, 
# ensuring the config reloads successfully but still breaks the traffic routing.
docker exec ${TARGET_CONTAINER} sh -c "echo 'server { listen 80; location / { proxy_pass http://127.0.0.1:8001; } }' > /etc/nginx/conf.d/default.conf && nginx -s reload"

if [ $? -eq 0 ]; then
    echo "Fault injected successfully."
else
    echo "Failed to inject fault."
    exit 1
fi