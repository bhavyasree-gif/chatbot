#!/usr/bin/env bash
# Run only against the disposable Lab 8.1 Compose project.
set -euo pipefail
cd "$(dirname "$0")/../.."
compose=(docker compose -p cti-replica-lab -f docker-compose-replicaset.yml)
primary=$("${compose[@]}" ps -q mongo-rs0-1)
secondary=$("${compose[@]}" ps -q mongo-rs0-2)
network=cti-replica-lab_default
if [ -z "$primary" ] || [ -z "$secondary" ]; then
    echo "Start the Lab 8.1 replica set first." >&2
    exit 1
fi
check() { "${compose[@]}" exec -T mongo-rs0-1 mongosh --quiet --eval "$1"; }
observe_secondary() {
    local expected=$1
    for attempt in {1..25}; do
        if check 'rs.status().members.find(m => m.name === "mongo-rs0-2:27017").health' 2>/dev/null | grep -qx "$expected"; then
            check 'printjson(rs.status().members.map(({name,stateStr,health}) => ({name,stateStr,health})))'
            return
        fi
        sleep 2
    done
    echo "Secondary did not reach the expected health state: $expected" >&2
    return 1
}

echo "Baseline topology"
observe_secondary 1
docker network disconnect "$network" "$secondary"
trap 'docker network connect --alias mongo-rs0-2 "$network" "$secondary" >/dev/null 2>&1 || true' EXIT
echo "Topology during secondary isolation"
observe_secondary 0
docker network connect --alias mongo-rs0-2 "$network" "$secondary"
trap - EXIT
echo "Topology after reconnection"
observe_secondary 1
