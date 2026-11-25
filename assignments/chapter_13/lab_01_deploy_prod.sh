#!/usr/bin/env bash
# Authenticated replica-set exercise. Use only the named local lab deployment.
set -euo pipefail
cd "$(dirname "$0")"
compose=(docker compose -p cti-secure-lab -f docker-compose-production.yml)

if [ -z "${CTI_LAB13_PASSWORD:-}" ]; then
    read -rs -p "Choose or enter the password for the local Lab 13 administrator: " CTI_LAB13_PASSWORD
    echo
fi
if [ "${#CTI_LAB13_PASSWORD}" -lt 12 ]; then
    echo "Use a lab-only password with at least 12 characters." >&2
    exit 1
fi
export CTI_LAB13_PASSWORD
umask 077
mkdir -p .lab13
if [ ! -s .lab13/keyfile ]; then
    openssl rand -base64 756 > .lab13/keyfile
fi
"${compose[@]}" up -d

mongo() { "${compose[@]}" exec -T -e CTI_LAB13_PASSWORD "$1" mongosh --quiet --eval "$2"; }
for member in prod-mongo-1 prod-mongo-2 prod-mongo-3; do
    for attempt in {1..45}; do
        if mongo "$member" 'db.adminCommand({ping:1}).ok' 2>/dev/null | grep -qx 1; then break; fi
        if [ "$attempt" -eq 45 ]; then echo "$member did not start." >&2; exit 1; fi
        sleep 2
    done
done

auth='const admin = db.getSiblingDB("admin"); admin.auth("cti_lab_admin", process.env.CTI_LAB13_PASSWORD);'
topology='printjson(rs.status().members.map(({name,stateStr,health}) => ({name,stateStr,health})));'
if mongo prod-mongo-1 "$auth $topology" 2>/dev/null; then
    echo "Existing authenticated lab verified."
    exit 0
fi

mongo prod-mongo-1 '
    const result = db.adminCommand({replSetInitiate:{
        _id:"cti-secure",
        members:[
            {_id:0,host:"prod-mongo-1:27017",priority:2},
            {_id:1,host:"prod-mongo-2:27017"},
            {_id:2,host:"prod-mongo-3:27017",arbiterOnly:true}
        ]
    }});
    if (!result.ok && result.code !== 23) quit(1);
'
for attempt in {1..45}; do
    if mongo prod-mongo-1 'db.hello().isWritablePrimary' | grep -qx true; then break; fi
    if [ "$attempt" -eq 45 ]; then echo "The expected primary did not become writable." >&2; exit 1; fi
    sleep 2
done
mongo prod-mongo-1 '
    db.getSiblingDB("admin").createUser({user:"cti_lab_admin",
        pwd:process.env.CTI_LAB13_PASSWORD,roles:[{role:"root",db:"admin"}]});
'
mongo prod-mongo-1 "$auth $topology"
echo "Authenticated replica-set status verified. Host port for prod-mongo-1: 27201."
