#!/bin/sh
docker exec app-01 tc qdisc add dev eth0 root netem loss 100%
echo "NIC Failure injected on app-01."