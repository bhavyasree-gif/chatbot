"""Prepare and start the local Windows presentation demo."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
MONGO_CONTAINER = "cti-mongo-labs"
MONGO_URI = "mongodb://127.0.0.1:27019/?directConnection=true"
API_URL = "http://127.0.0.1:5000/api/health"
FRONTEND_URL = "http://127.0.0.1:5173/"
OLLAMA_URL = "http://127.0.0.1:11434"


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def capture(command):
    return run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()


def wait_until(probe, seconds, failure):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if probe():
            return
        time.sleep(2)
    raise RuntimeError(failure)


def http_ready(url):
    try:
        with urlopen(url, timeout=2) as response:
            return response.status == 200
    except (URLError, OSError):
        return False


def ensure_ports_free():
    for port in (5000, 5173):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(
                    f"Cannot bind local port {port}: {exc}. "
                    "Close any earlier CTI Sentinel server using this port and rerun."
                ) from exc


def npm_command(*args):
    return [os.environ.get("ComSpec", "cmd.exe"), "/d", "/c", "npm.cmd", *args]


def prepare_mongo():
    if not shutil.which("docker"):
        raise RuntimeError("Install Docker Desktop for Windows and reopen this launcher.")
    def engine_ready():
        try:
            return bool(capture(["docker", "info", "--format", "{{.ServerVersion}}"]))
        except subprocess.CalledProcessError:
            return False

    if not engine_ready():
        desktop = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe"
        if desktop.is_file():
            subprocess.Popen([str(desktop)], cwd=ROOT)
        wait_until(engine_ready, 90, "Open Docker Desktop, wait for Engine running, then rerun.")

    state = capture(["docker", "ps", "-a", "--filter", f"name=^/{MONGO_CONTAINER}$",
                     "--format", "{{.State}}"])
    if not state:
        run(["docker", "compose", "-f", "docker-compose-labs.yml", "up", "-d"])
    elif state != "running":
        run(["docker", "start", MONGO_CONTAINER])

    shell = ["docker", "exec", MONGO_CONTAINER, "mongosh", "--quiet", "--eval"]
    def mongo_check(expression, expected):
        try:
            return capture([*shell, expression]) == expected
        except subprocess.CalledProcessError:
            return False

    wait_until(lambda: mongo_check("db.adminCommand({ping:1}).ok", "1"), 45,
               f"MongoDB did not start. Check docker logs {MONGO_CONTAINER}.")
    run([*shell,
         "try { rs.status() } catch (e) {"
         " if (e.codeName !== 'NotYetInitialized' && e.code !== 94) throw e;"
         " rs.initiate({_id:'rs0',members:[{_id:0,host:'localhost:27017'}]});"
         " }"])
    wait_until(lambda: mongo_check("db.hello().isWritablePrimary", "true"), 45,
               "The lab replica set did not elect a primary.")


def prepare_ollama():
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    executable = shutil.which("ollama") or (str(local) if local.is_file() else None)
    if not executable:
        raise RuntimeError("Install Ollama for Windows from https://ollama.com/download/windows.")
    if not http_ready(f"{OLLAMA_URL}/api/tags"):
        subprocess.Popen([executable, "serve"], cwd=ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE)
        wait_until(lambda: http_ready(f"{OLLAMA_URL}/api/tags"), 40,
                   "Ollama did not start. Check the Ollama window and rerun.")
    for model in ("qwen2.5:3b", "nomic-embed-text"):
        try:
            capture([executable, "show", model])
        except subprocess.CalledProcessError:
            run([executable, "pull", model])


def configure_environment():
    # Process settings take precedence over dotenv for this local demo.
    os.environ.update(
        AI_PROVIDER="ollama",
        OLLAMA_HOST=OLLAMA_URL,
        OLLAMA_BASE_URL=OLLAMA_URL,
        OLLAMA_MODEL="qwen2.5:3b",
        OLLAMA_EMBED_MODEL="nomic-embed-text",
        MONGO_URI=MONGO_URI,
        MONGO_LABS_URI=MONGO_URI,
        DATABASE_NAME="ctiSentinelDemo",
        ENABLE_LAB_RUNNER="1",
        FLASK_HOST="127.0.0.1",
        FLASK_PORT="5000",
    )


def install_dependencies():
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    if not python.is_file():
        run([sys.executable, "-m", "venv", ".venv"])
    run([str(python), "-m", "pip", "install", "-r", "requirements.txt"])
    if not (FRONTEND / "node_modules" / "vite" / "bin" / "vite.js").is_file():
        run(npm_command("--prefix", "frontend", "ci"))
    return str(python)


def seed_demo(python):
    run([python, "-c",
         "from backend.config.connection import get_db; "
         "from backend.scripts.seed import main; "
         "collections = {'threats', 'sources', 'threat_actors', 'threats_embedded'}; "
         "main() if collections.isdisjoint(get_db().list_collection_names()) else None"])
    run([python, "-m", "backend.scripts.ingest_threat_knowledge"])


def launch():
    if sys.platform != "win32":
        raise RuntimeError("This launcher is for Windows. See the README for Docker setup.")
    if not shutil.which("npm.cmd"):
        raise RuntimeError("Install Node.js for Windows and reopen this launcher.")
    ensure_ports_free()
    configure_environment()
    print("Preparing the isolated Docker lab and Ollama. First-time downloads may take a few minutes.", flush=True)
    prepare_mongo()
    prepare_ollama()
    python = install_dependencies()
    seed_demo(python)

    processes = []
    try:
        for command in ([python, "-m", "backend.app"], npm_command("--prefix", "frontend", "run", "dev", "--", "--host", "127.0.0.1")):
            processes.append(subprocess.Popen(command, cwd=ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE))
        wait_until(lambda: http_ready(API_URL) and http_ready(FRONTEND_URL), 40,
                   "The app did not finish starting. Check the two server windows for errors.")
    except (OSError, RuntimeError):
        for process in processes:
            if process.poll() is None:
                process.terminate()
        raise

    print(f"CTI Sentinel is ready at {FRONTEND_URL}. Keep both server windows open.")
    webbrowser.open(FRONTEND_URL)


if __name__ == "__main__":
    try:
        launch()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr.strip(), file=sys.stderr)
        print(f"Setup stopped: {exc}", file=sys.stderr)
        sys.exit(1)
