"""Lab 8.2 - Observe Failover and Election
PyMongo failover observer script.
Requires a running replica set (use Lab 8.1 docker-compose).
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pymongo import MongoClient
from backend.config.connection import banner

RS_URI = os.getenv(
    "REPLICA_SET_URI",
    "mongodb://127.0.0.1:27101/?directConnection=true"
)


def get_rs_status(client):
    """Get replica set member statuses."""
    status = client.admin.command("replSetGetStatus")
    members = []
    for m in status["members"]:
        members.append({
            "name": m["name"],
            "state_str": m["stateStr"],
            "health": m["health"],
        })
    return members


def observe_failover(interval=2, duration=60):
    """Monitor replica set state and detect primary changes."""
    print("Connecting to the configured replica-set observer address.")
    client = MongoClient(RS_URI, serverSelectionTimeoutMS=5000,
                         socketTimeoutMS=3000, connectTimeoutMS=5000)
    client.admin.command("ping")
    print("[OK] Connected to replica set.")
    print(f"Monitoring every {interval}s for {duration}s...")
    print("[TIP] In another terminal, run:")
    print('  docker exec mongo-rs0-1 mongosh --eval \'rs.stepDown()\'')
    print()

    last_primary = None
    start = time.time()
    try:
        while time.time() - start < duration:
            try:
                members = get_rs_status(client)
                primary = None
                for m in members:
                    if m["state_str"] == "PRIMARY":
                        primary = m["name"]
                if primary and primary != last_primary:
                    ts = time.strftime("%H:%M:%S")
                    if last_primary is None:
                        print(f"  [{ts}] PRIMARY detected: {primary}")
                    else:
                        print(f"  [{ts}] *** FAILOVER: {last_primary} -> {primary} ***")
                    last_primary = primary
                time.sleep(interval)
            except Exception as e:
                print(f"  [WARN] Connection issue: {e}")
                time.sleep(interval)
    except KeyboardInterrupt:
        pass
    print(f"\nMonitoring stopped. Final primary: {last_primary}")
    client.close()


def main():
    banner("Lab 8.2: Observe Failover and Election")
    observe_failover(interval=2, duration=60)
    banner("Lab 8.2 Complete")


if __name__ == "__main__":
    main()