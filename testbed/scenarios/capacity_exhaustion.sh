#!/bin/sh
docker update --cpus="0.1" --memory="64m" db-01
echo "Capacity exhaustion injected on db-01."