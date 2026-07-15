#!/bin/sh
docker exec loadgen sh -c "apk add --no-cache nmap && nmap -p 1-1000 lb-01"
echo "Port scan injected from loadgen to lb-01."