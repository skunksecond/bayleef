import os
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

_SERVER_PROCESS = None
_EXIT_CALLBACK = None
_STATUS_TEXT = "Entralinked idle."
_STATUS_HISTORY = deque([_STATUS_TEXT], maxlen=8)
_STATUS_LOCK = threading.Lock()
_PROCESS_ENV = None
_STOP_REQUESTED = False
_LAUNCH_TIME = 0.0


def get_jar_path() -> Path:
    return Path(__file__).resolve().parent / "third_party" / "entralinked" / "entralinked.jar"


def get_status_text() -> str:
    return _STATUS_TEXT


def get_status_lines() -> list[str]:
    with _STATUS_LOCK:
        return list(_STATUS_HISTORY)


def _set_status(message: str):
    global _STATUS_TEXT
    message = " ".join(str(message).split())
    if not message:
        return
    with _STATUS_LOCK:
        _STATUS_TEXT = message
        if not _STATUS_HISTORY or _STATUS_HISTORY[-1] != message:
            _STATUS_HISTORY.append(message)


def _reset_status(message: str):
    global _STATUS_TEXT
    with _STATUS_LOCK:
        _STATUS_TEXT = message
        _STATUS_HISTORY.clear()
        _STATUS_HISTORY.append(message)


def _build_process_environment() -> dict[str, str]:
    env = os.environ.copy()
    if not sys.platform.startswith("linux"):
        return env

    if not env.get("DISPLAY"):
        x11_socket_dir = Path("/tmp/.X11-unix")
        if x11_socket_dir.is_dir():
            displays = sorted(x11_socket_dir.glob("X*"))
            if displays:
                env["DISPLAY"] = f":{displays[0].name[1:]}"

    if not env.get("XAUTHORITY"):
        authority_file = Path.home() / ".Xauthority"
        if authority_file.is_file():
            env["XAUTHORITY"] = str(authority_file)

    return env


def _append_log_failure_details():
    log_path = get_jar_path().parent / "logs" / "latest.log"
    try:
        if not log_path.is_file() or log_path.stat().st_mtime < _LAUNCH_TIME - 2:
            return
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
    except OSError:
        return

    markers = (" error ", "exception", "caused by", "denied", "failed", "address already")
    details = [line.strip() for line in lines if any(marker in line.lower() for marker in markers)]
    for line in details[-3:]:
        _set_status(line[:300])

    combined_details = " ".join(details).lower()
    if "bindexception" in combined_details or "permission denied" in combined_details:
        _set_status("Linux blocked Entralinked from binding required ports 53, 80, or 443.")
        _set_status("For this boot: sudo sysctl -w net.ipv4.ip_unprivileged_port_start=53")

    if not details:
        _set_status(f"More details may be in {log_path}")


def _run_command(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=_PROCESS_ENV,
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


def _consume_server_output(process):
    if process.stdout is None:
        return

    try:
        for line in process.stdout:
            text = line.strip()
            if text:
                _set_status(text[:300])
    except Exception:
        pass


def _prepare_linux_window(process):
    if not sys.platform.startswith("linux"):
        return

    deadline = time.time() + 15
    while process.poll() is None and time.time() < deadline:
        window_id = _find_window_id_for_pid(process.pid)
        if window_id:
            _position_linux_window(window_id)
            return
        time.sleep(0.2)

    if process.poll() is None:
        _set_status("Entralinked launched, but its window was not detected.")


def _watch_server_process(process, output_watcher):
    global _SERVER_PROCESS

    return_code = process.wait()
    output_watcher.join(timeout=1)
    if _SERVER_PROCESS is process:
        _SERVER_PROCESS = None

    if not _STOP_REQUESTED:
        _append_log_failure_details()
        _set_status(f"Entralinked exited unexpectedly (Java exit code {return_code}).")
        if sys.platform.startswith("linux"):
            display = (_PROCESS_ENV or {}).get("DISPLAY", "not set")
            _set_status(f"X11 display used: {display}")


def request_exit(callback=None):
    global _EXIT_CALLBACK

    active_callback = callback if callback is not None else _EXIT_CALLBACK
    _EXIT_CALLBACK = None
    stop_entralinked()

    if active_callback is not None:
        active_callback()


def start_entralinked(exit_callback=None):
    global _SERVER_PROCESS, _EXIT_CALLBACK, _PROCESS_ENV, _STOP_REQUESTED, _LAUNCH_TIME

    if _SERVER_PROCESS is not None:
        return

    _EXIT_CALLBACK = exit_callback

    jar_path = get_jar_path()
    if not jar_path.exists():
        _reset_status(f"Entralinked jar not found: {jar_path}")
        return False

    _STOP_REQUESTED = False
    _LAUNCH_TIME = time.time()
    _PROCESS_ENV = _build_process_environment()
    _reset_status("Launching Entralinked...")

    java_path = shutil.which("java", path=_PROCESS_ENV.get("PATH"))
    if not java_path:
        _set_status("Java was not found. Install a JRE and make sure java is on PATH.")
        return False

    if sys.platform.startswith("linux") and not _PROCESS_ENV.get("DISPLAY"):
        _set_status("No X11 display was found. Start Bayleef inside an X11 session.")
        _set_status("For an autostart service, pass DISPLAY=:0 and XAUTHORITY to Bayleef.")
        return False

    try:
        _SERVER_PROCESS = subprocess.Popen(
            [java_path, "-Djava.awt.headless=false", "-jar", str(jar_path)],
            cwd=str(jar_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=_PROCESS_ENV,
        )
    except OSError as error:
        _set_status(f"Could not start Java: {error}")
        _SERVER_PROCESS = None
        return False

    process = _SERVER_PROCESS
    _set_status(f"Java started (PID {process.pid}). Waiting for the Swing window...")

    output_watcher = threading.Thread(target=_consume_server_output, args=(process,), daemon=True)
    output_watcher.start()

    linux_window_watcher = threading.Thread(target=_prepare_linux_window, args=(process,), daemon=True)
    linux_window_watcher.start()

    server_watcher = threading.Thread(
        target=_watch_server_process,
        args=(process, output_watcher),
        daemon=True,
    )
    server_watcher.start()
    return True


def stop_entralinked():
    global _SERVER_PROCESS, _EXIT_CALLBACK, _STOP_REQUESTED

    _STOP_REQUESTED = True
    if _SERVER_PROCESS is not None:
        _SERVER_PROCESS.terminate()
        try:
            _SERVER_PROCESS.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _SERVER_PROCESS.kill()
        _SERVER_PROCESS = None

    _EXIT_CALLBACK = None
    _set_status("Entralinked closed.")
