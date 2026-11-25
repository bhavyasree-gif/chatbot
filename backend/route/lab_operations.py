"""Safe read-only lab checks and opt-in write concern benchmark."""
import os
from math import ceil
from statistics import mean
import time
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from pymongo.write_concern import WriteConcern
from backend.config.connection import get_client
from pymongo import MongoClient

bp = Blueprint("lab_operations", __name__)

@bp.get("/labs/replica/status")
def replica_status():
    uri = os.getenv("MONGO_LABS_URI")
    lab_client = MongoClient(uri, serverSelectionTimeoutMS=5000) if uri else None
    try:
        status = (lab_client if lab_client is not None else get_client()).admin.command("replSetGetStatus")
        return jsonify(ok=True, set=status.get("set"), members=[{"name": m.get("name"), "state": m.get("stateStr"), "health": m.get("health")} for m in status.get("members", [])])
    except Exception:
        return jsonify(ok=False, error="Replica set inspection failed. Check the lab MongoDB connection."), 422
    finally:
        if lab_client is not None:
            lab_client.close()

@bp.get("/labs/14/1/metrics")
def metrics():
    try:
        server = get_client().admin.command("serverStatus")
        cache = server.get("wiredTiger", {}).get("cache", {})
        read = cache.get("bytes read into cache", 0)
        requested = cache.get("bytes requested from the cache", 0)
        # This is an illustrative byte-based proxy, not an official hit ratio.
        proxy = round(100 * (1 - read / requested), 2) if requested else None
        return jsonify(connections=server.get("connections", {}), opcounters=server.get("opcounters", {}), cache_bytes=cache.get("bytes currently in the cache"), cache_hit_proxy_percent=proxy, cache_hit_proxy_caveat="Approximation; WiredTiger counters are not a canonical hit ratio")
    except Exception as exc:
        return jsonify(error=str(exc)), 422

@bp.post("/labs/9/1/benchmark")
def benchmark():
    if os.getenv("ENABLE_LAB_RUNNER") != "1":
        return jsonify(error="Set ENABLE_LAB_RUNNER=1 for local benchmarking"), 403
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify(error="Benchmark only available from localhost"), 403
    if request.get_json(silent=True) != {"confirm": "isolated-lab"}:
        return jsonify(error="Explicit isolated-lab confirmation required"), 400
    uri = os.getenv("MONGO_LABS_URI")
    if not uri:
        return jsonify(error="Configure MONGO_LABS_URI for a dedicated test replica set first"), 422
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        members = client.admin.command("replSetGetConfig")["config"]["members"]
        if len(members) < 3:
            client.close()
            return jsonify(error="Three-node replica set required"), 422
    except Exception as exc:
        client.close()
        return jsonify(error="Replica set required: " + str(exc)), 422
    data_members = sum(not member.get("arbiterOnly", False) for member in members)
    results = []
    db = client["cti_sentinel_labs_sandbox"]
    for journal in (False, True):
        for name, w in (("w:1", 1), ("w:majority", "majority"), ("w:all", data_members)):
            col = db.get_collection("lab09_write_benchmark", write_concern=WriteConcern(w=w, j=journal, wtimeout=8000))
            run_id = f"{int(time.time() * 1000)}-{name}-{journal}"
            start = time.perf_counter()
            samples = []
            error = None
            try:
                for i in range(1000):
                    write_start = time.perf_counter()
                    col.insert_one({"run_id": run_id, "sequence": i, "created_at": datetime.now(timezone.utc)})
                    samples.append(1000 * (time.perf_counter() - write_start))
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            elapsed = time.perf_counter() - start
            samples.sort()
            completed = len(samples)
            results.append({
                "write_concern": name, "journal": journal, "completed": completed,
                "total_seconds": round(elapsed, 4),
                "avg_ms_per_completed_write": round(mean(samples), 4) if samples else None,
                "p50_ms": round(samples[ceil(.50 * completed) - 1], 4) if samples else None,
                "p99_ms": round(samples[ceil(.99 * completed) - 1], 4) if samples else None,
                "error": error,
            })
    client.close()
    return jsonify(results=results, passed=all(row["completed"] == 1000 for row in results), note="Each combination runs 1,000 sequential writes; results depend on actual replica set and storage configuration.")
