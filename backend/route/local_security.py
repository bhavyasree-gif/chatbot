"""Windows-only Docker inventory and Microsoft Defender scans."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from threading import Lock, Thread

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

bp = Blueprint("local_security", __name__, url_prefix="/local-security")
_lock = Lock()
_scan = {"status": "idle"}
_file_limit = 50 * 1024 * 1024
_origins = {f"http://{host}:{port}" for host in ("localhost", "127.0.0.1")
            for port in (5000, 5173)}

@bp.errorhandler(RequestEntityTooLarge)
def upload_too_large(_error):
    return jsonify(error="The file is larger than 50 MB."), 413


@bp.before_request
def local_only():
    if (os.name != "nt" or os.getenv("ENABLE_LOCAL_SECURITY") != "1"
            or request.remote_addr not in ("127.0.0.1", "::1")
            or f"http://{request.host}" not in _origins
            or request.headers.get("Origin", f"http://{request.host}") not in _origins
            or request.headers.get("X-CTI-Local") != "1"):
        return jsonify(error="Use the Windows launcher and open the dashboard on localhost."), 403


@bp.get("/images")
def images():
    try:
        result = subprocess.run(
            ["docker.exe", "--host", "npipe:////./pipe/docker_engine", "image", "ls",
             "--all", "--no-trunc", "--format", "{{json .}}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=12,
        )
        if result.returncode:
            return jsonify(error="Docker Engine is unavailable. Open Docker Desktop and check its engine status."), 503
        return jsonify(images=[json.loads(line) for line in result.stdout.splitlines() if line.strip()])
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return jsonify(error="Could not read the local Docker image inventory."), 503


def defender_path():
    platform = Path(os.environ["ProgramData"]) / "Microsoft/Windows Defender/Platform"
    candidates = sorted(platform.glob("*/MpCmdRun.exe"), reverse=True)
    candidates.append(Path(os.environ["ProgramFiles"]) / "Windows Defender/MpCmdRun.exe")
    return next((path for path in candidates if path.is_file()), None)


def _run_scan(command, kind, directory):
    try:
        result = subprocess.run(command, capture_output=True, text=True, errors="replace",
                                timeout={"file": 600, "quick": 86400, "full": 604800}[kind])
        output = (result.stdout + "\n" + result.stderr).strip()[-12000:]
        if result.returncode == 0:
            status = "completed"
            summary = ("Defender finished scanning the file and reported no detection."
                       if kind == "file" else
                       "Defender finished. Check Windows Security → Protection history for detections and actions.")
        elif result.returncode == 2:
            status = "review"
            summary = "Defender reported a threat, required action, or encountered a scan error. Review the output."
        else:
            status = "failed"
            summary = "Defender could not complete the scan."
        details = {"status": status, "summary": summary, "output": output, "exit_code": result.returncode}
    except (OSError, subprocess.TimeoutExpired):
        details = {"status": "failed", "summary": "Defender could not finish. Check Windows Security for scan status."}
    finally:
        if directory:
            directory.cleanup()
    with _lock:
        _scan.update(details)


@bp.get("/scan")
def scan_status():
    with _lock:
        return jsonify(_scan)


@bp.post("/scan/<kind>")
def start_scan(kind):
    if kind not in ("file", "quick", "full"):
        return jsonify(error="Unknown scan type."), 404
    executable = defender_path()
    if executable is None:
        return jsonify(error="Microsoft Defender Antivirus was not found."), 503

    with _lock:
        if _scan["status"] == "running":
            return jsonify(error="A scan is already running."), 409
        metadata = {"kind": kind, "status": "running"}
        directory = None
        command = [str(executable), "-Scan", "-ScanType", {"quick": "1", "full": "2", "file": "3"}[kind]]
        if kind == "file":
            request.max_content_length = _file_limit + 65536
            upload = request.files.get("file")
            if not upload or not upload.filename:
                return jsonify(error="Select a file to scan."), 400
            content = upload.stream.read(_file_limit + 1)
            if len(content) > _file_limit:
                return jsonify(error="The file is larger than 50 MB."), 413
            suffix = Path(upload.filename).suffix
            suffix = suffix if re.fullmatch(r"\.[a-zA-Z0-9]{1,12}", suffix) else ""
            directory = tempfile.TemporaryDirectory(prefix="cti-scan-", ignore_cleanup_errors=True)
            path = Path(directory.name) / f"sample{suffix}"
            try:
                path.write_bytes(content)
            except OSError:
                directory.cleanup()
                return jsonify(error="Windows blocked access to the scan copy. Check Protection history."), 422
            command.extend(["-File", str(path), "-DisableRemediation"])
            metadata.update(filename=Path(upload.filename).name, sha256=hashlib.sha256(content).hexdigest())
        _scan.clear()
        _scan.update(metadata)
        worker = Thread(target=_run_scan, args=(command, kind, directory), daemon=True)
        try:
            worker.start()
        except RuntimeError:
            if directory:
                directory.cleanup()
            _scan.update(status="failed", summary="Could not start the scan.")
            return jsonify(_scan), 503
        return jsonify(metadata), 202
