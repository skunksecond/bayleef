import subprocess
import threading
from pathlib import Path

_SERVER_PROCESS = None
_EXIT_CALLBACK = None


def get_default_entralinked_url() -> str:
    return "http://127.0.0.1"


def get_jar_path() -> Path:
    return Path(__file__).resolve().parent / "third_party" / "entralinked" / "entralinked.jar"


def _watch_server_process():
    global _SERVER_PROCESS

    if _SERVER_PROCESS is None:
        return

    try:
        _SERVER_PROCESS.wait(timeout=1)
    except subprocess.TimeoutExpired:
        return

    request_exit()


def request_exit(callback=None):
    global _EXIT_CALLBACK

    active_callback = callback if callback is not None else _EXIT_CALLBACK
    _EXIT_CALLBACK = None
    stop_entralinked()

    if active_callback is not None:
        active_callback()


def start_entralinked(exit_callback=None):
    global _SERVER_PROCESS, _EXIT_CALLBACK

    if _SERVER_PROCESS is not None:
        return

    _EXIT_CALLBACK = exit_callback

    jar_path = get_jar_path()
    if not jar_path.exists():
        raise FileNotFoundError(f"Entralinked jar not found: {jar_path}")

    _SERVER_PROCESS = subprocess.Popen(
        ["java", "-jar", str(jar_path)],
        cwd=str(jar_path.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    server_watcher = threading.Thread(target=_watch_server_process, daemon=True)
    server_watcher.start()


def stop_entralinked():
    global _SERVER_PROCESS, _EXIT_CALLBACK

    if _SERVER_PROCESS is not None:
        _SERVER_PROCESS.terminate()
        try:
            _SERVER_PROCESS.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _SERVER_PROCESS.kill()
        _SERVER_PROCESS = None

    _EXIT_CALLBACK = None
