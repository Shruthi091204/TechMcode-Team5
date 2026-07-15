#!/bin/sh
docker exec loadgen sh -c "for i in \$(seq 1 500); do curl -s http://lb-01 > /dev/null & done"
echo "DDoS flood injected against lb-01."