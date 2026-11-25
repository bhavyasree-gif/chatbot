#!/usr/bin/env bash
# Standalone, disposable local replica-set lab.
set -euo pipefail
cd "$(dirname "$0")/../.."

compose=(docker compose -p cti-replica-lab -f docker-compose-replicaset.yml)
"${compose[@]}" up -d
mongo() { "${compose[@]}" exec -T "$1" mongosh --quiet --eval "$2"; }

for member in mongo-rs0-1 mongo-rs0-2 mongo-rs0-3; do
    for attempt in {1..45}; do
        if mongo "$member" 'db.adminCommand({ping:1}).ok' 2>/dev/null | grep -qx 1; then break; fi
        if [ "$attempt" -eq 45 ]; then echo "$member did not start." >&2; exit 1; fi
        sleep 2
    done
done

mongo mongo-rs0-1 'try { rs.status() } catch (err) {
    if (err.code !== 94) throw err;
    rs.initiate({_id:"rs0",members:[
        {_id:0, host:"mongo-rs0-1:27017", priority:2},
        {_id:1, host:"mongo-rs0-2:27017"},
        {_id:2, host:"mongo-rs0-3:27017", arbiterOnly:true}
    ]});
}'

for attempt in {1..45}; do
    if mongo mongo-rs0-1 'db.hello().isWritablePrimary' 2>/dev/null | grep -qx true; then break; fi
    if [ "$attempt" -eq 45 ]; then echo "The expected primary did not become writable." >&2; exit 1; fi
    sleep 2
done
mongo mongo-rs0-1 '
    const result = db.getSiblingDB("cti_lab8").replication.replaceOne(
        {_id:"lab8.1"}, {note:"Replication verification"},
        {upsert:true,writeConcern:{w:2,wtimeout:10000}});
    if (!result.acknowledged) quit(1);
    printjson(rs.status().members.map(({name,stateStr,health}) => ({name,stateStr,health})));
'
mongo mongo-rs0-2 '
    db.getMongo().setReadPref("secondary");
    const copy = db.getSiblingDB("cti_lab8").replication.findOne({_id:"lab8.1"});
    if (!copy) quit(1);
    printjson(copy);
'
echo "Replication verified. Primary host URI: mongodb://127.0.0.1:27101/?directConnection=true"
