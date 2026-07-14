#!/bin/sh
# testbed/scenarios/link_degradation.sh
# Injects 500ms latency and 5% packet loss on db-01

TARGET_CONTAINER="db-01"
DELAY="500ms"
LOSS="5%"

echo "Injecting link degradation on ${TARGET_CONTAINER} (Delay: ${DELAY}, Loss: ${LOSS})..."

# Add the netem qdisc (queueing discipline) to the root of the eth0 interface
docker exec ${TARGET_CONTAINER} tc qdisc add dev eth0 root netem delay ${DELAY} loss ${LOSS}

if [ $? -eq 0 ]; then
    echo "Fault injected successfully."
else
    echo "Failed to inject fault. Check NET_ADMIN capabilities."
    exit 1
fi