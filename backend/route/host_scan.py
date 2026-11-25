"""Opt-in, loopback-only host scanning with same-origin and per-process token checks."""
import os
import platform
import secrets
import threading
from urllib.parse import urlsplit
from flask import Blueprint, jsonify, request
from backend.services.host_scan import scan

bp = Blueprint("host_scan", __name__)
_token = secrets.token_urlsafe(32)
_lock = threading.Lock()
_ALLOWED = {"localhost", "127.0.0.1", "::1"}

@bp.before_request
def local_only():
    if request.remote_addr not in {"127.0.0.1", "::1"} or urlsplit(request.host_url).hostname not in _ALLOWED:
        return jsonify(error="Host scanning is available only through localhost."), 403
    origin = request.headers.get("Origin")
    if origin and origin not in {"http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5000", "http://127.0.0.1:5000"}:
        return jsonify(error="Untrusted origin."), 403
    if request.headers.get("Sec-Fetch-Site") == "cross-site":
        return jsonify(error="Cross-site scanning is blocked."), 403

@bp.get("/host-scan/status")
def status():
    enabled = os.getenv("ENABLE_HOST_SCAN") == "1"
    return jsonify(enabled=enabled, supported=platform.system() == "Windows", token=_token if enabled else None,
                   message="Set ENABLE_HOST_SCAN=1 and restart the backend to enable read-only Windows checks.")

@bp.post("/host-scan")
def run_scan():
    if os.getenv("ENABLE_HOST_SCAN") != "1":
        return jsonify(error="Host scanning is disabled. Set ENABLE_HOST_SCAN=1 and restart the backend."), 403
    if not secrets.compare_digest(request.headers.get("X-Scan-Token", ""), _token):
        return jsonify(error="Refresh the scan page before scanning."), 403
    if not request.is_json or request.get_json(silent=True) != {"consent": True}:
        return jsonify(error="Explicit scan consent is required."), 400
    if not _lock.acquire(blocking=False):
        return jsonify(error="A scan is already running."), 409
    try:
        return jsonify(scan())
    finally:
        _lock.release()
