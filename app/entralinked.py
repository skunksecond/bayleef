import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

_SERVER_PROCESS = None
_EXIT_CALLBACK = None
_STATUS_TEXT = "Entralinked idle."


def get_jar_path() -> Path:
    return Path(__file__).resolve().parent / "third_party" / "entralinked" / "entralinked.jar"


def get_status_text() -> str:
    return _STATUS_TEXT


def _set_status(message: str):
    global _STATUS_TEXT
    _STATUS_TEXT = message


def _run_command(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout


def _find_window_id_for_pid(pid: int) -> str | None:
    if shutil.which("xdotool"):
        output = _run_command(["xdotool", "search", "--pid", str(pid)])
        if output:
            window_ids = [line.strip() for line in output.splitlines() if line.strip()]
            if window_ids:
                return window_ids[0]

    if shutil.which("wmctrl"):
        output = _run_command(["wmctrl", "-lp"])
        if output:
            for line in output.splitlines():
                parts = line.split(None, 4)
                if len(parts) >= 3 and parts[2] == str(pid):
                    return parts[0]

    return None


def _find_bayleef_window_id() -> str | None:
    if shutil.which("xdotool"):
        output = _run_command(["xdotool", "search", "--name", "Bayleef"])
        if output:
            window_ids = [line.strip() for line in output.splitlines() if line.strip()]
            if window_ids:
                return window_ids[0]
    return None


def _window_geometry(window_id: str) -> tuple[int, int, int, int] | None:
    if not shutil.which("xdotool"):
        return None

    output = _run_command(["xdotool", "getwindowgeometry", "--shell", window_id])
    if not output:
        return None

    values = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    try:
        return (
            int(values["X"]),
            int(values["Y"]),
            int(values["WIDTH"]),
            int(values["HEIGHT"]),
        )
    except (KeyError, ValueError):
        return None


def _position_linux_window(window_id: str):
    if not shutil.which("wmctrl"):
        _set_status("Entralinked launched. Install wmctrl for overlay placement.")
        return

    geometry = None
    bayleef_window = _find_bayleef_window_id()
    if bayleef_window:
        geometry = _window_geometry(bayleef_window)

    if geometry:
        x, y, width, height = geometry
        _run_command(["wmctrl", "-i", "-r", window_id, "-e", f"0,{x},{y},{width},{height}"])
        _set_status("Entralinked window aligned over Bayleef.")
    else:
        _set_status("Entralinked launched. Bayleef window position unavailable.")

    _run_command(["wmctrl", "-i", "-r", window_id, "-b", "add,above"])
    if shutil.which("xdotool"):
        _run_command(["xdotool", "windowactivate", window_id])


def _consume_server_output():
    if _SERVER_PROCESS is None or _SERVER_PROCESS.stdout is None:
        return

    try:
        for line in _SERVER_PROCESS.stdout:
            text = line.strip()
            if text:
                _set_status(text[:140])
    except Exception:
        pass


def _prepare_linux_window():
    if _SERVER_PROCESS is None or not sys.platform.startswith("linux"):
        return

    deadline = time.time() + 15
    while _SERVER_PROCESS is not None and time.time() < deadline:
        window_id = _find_window_id_for_pid(_SERVER_PROCESS.pid)
        if window_id:
            _position_linux_window(window_id)
            return
        time.sleep(0.2)

    if _SERVER_PROCESS is not None:
        _set_status("Entralinked launched, but its window was not detected.")


def _watch_server_process():
    global _SERVER_PROCESS

    if _SERVER_PROCESS is None:
        return

    _SERVER_PROCESS.wait()
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

    _set_status("Launching Entralinked...")
    _SERVER_PROCESS = subprocess.Popen(
        ["java", "-jar", str(jar_path)],
        cwd=str(jar_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_watcher = threading.Thread(target=_consume_server_output, daemon=True)
    output_watcher.start()

    linux_window_watcher = threading.Thread(target=_prepare_linux_window, daemon=True)
    linux_window_watcher.start()

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
    _set_status("Entralinked closed.")
