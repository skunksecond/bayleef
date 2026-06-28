from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading

_SERVER = None
_SERVER_THREAD = None
_BROWSER_PROCESS = None
_BROWSER_PROFILE = None
_EXIT_CALLBACK = None
_STOP_REQUESTED = False
_STATUS_TEXT = "EonTimer idle."


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


class EonTimerHandler(QuietHandler):
    def do_GET(self):
        if self.path.startswith("/eontimer/close"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"closing")
            threading.Thread(target=request_exit, daemon=True).start()
            return

        super().do_GET()


def get_status_text() -> str:
    return _STATUS_TEXT


def _set_status(message: str):
    global _STATUS_TEXT
    _STATUS_TEXT = message


def _get_eontimer_dir() -> Path:
    return Path(__file__).resolve().parent / "third_party" / "eontimer" / "EonTimer"


def _find_chromium() -> str | None:
    if sys.platform.startswith("win"):
        candidates = [
            Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return shutil.which("chrome") or shutil.which("msedge")

    if sys.platform == "darwin":
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        return str(chrome) if chrome.is_file() else None

    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        executable = shutil.which(name)
        if executable:
            return executable
    return None


def _browser_command(browser: str, url: str, profile_dir: str) -> list[str]:
    command = [
        browser,
        f"--app={url}",
        "--kiosk",
        "--window-position=0,0",
        "--window-size=800,480",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--noerrdialogs",
        "--disable-session-crashed-bubble",
        "--disable-translate",
        "--password-store=basic",
    ]
    if sys.platform.startswith("linux"):
        command.append("--ozone-platform=x11")
    return command


def _watch_browser_process(process):
    process.wait()
    if _BROWSER_PROCESS is process and not _STOP_REQUESTED:
        request_exit()


def request_exit(callback=None):
    global _EXIT_CALLBACK

    active_callback = callback if callback is not None else _EXIT_CALLBACK
    _EXIT_CALLBACK = None
    stop_eontimer()

    if active_callback is not None:
        active_callback()


def start_eontimer(exit_callback=None):
    global _SERVER, _SERVER_THREAD, _BROWSER_PROCESS, _BROWSER_PROFILE
    global _EXIT_CALLBACK, _STOP_REQUESTED

    if _SERVER is not None:
        return True

    _EXIT_CALLBACK = exit_callback
    _STOP_REQUESTED = False
    eontimer_dir = _get_eontimer_dir()

    if not eontimer_dir.is_dir():
        _set_status(f"EonTimer directory not found: {eontimer_dir}")
        return False

    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        _set_status("No X11 display found. Start Bayleef using ./run.sh")
        return False

    browser = _find_chromium()
    if not browser:
        _set_status("No Chromium browser found. Install chromium or chromium-browser.")
        return False

    handler = partial(EonTimerHandler, directory=str(eontimer_dir))
    try:
        _SERVER = ThreadingHTTPServer(("127.0.0.1", 8000), handler)
    except OSError as error:
        _set_status(f"Could not start EonTimer server on port 8000: {error}")
        return False

    _SERVER_THREAD = threading.Thread(target=_SERVER.serve_forever, daemon=True)
    _SERVER_THREAD.start()

    _BROWSER_PROFILE = tempfile.mkdtemp(prefix="bayleef-eontimer-")
    command = _browser_command(browser, "http://127.0.0.1:8000/", _BROWSER_PROFILE)
    popen_options = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform.startswith("linux"):
        popen_options["start_new_session"] = True

    try:
        _BROWSER_PROCESS = subprocess.Popen(command, **popen_options)
    except OSError as error:
        failure = f"Could not open EonTimer in {browser}: {error}"
        stop_eontimer()
        _set_status(failure)
        return False

    _set_status(f"EonTimer opened in {Path(browser).name}.")
    watcher = threading.Thread(
        target=_watch_browser_process,
        args=(_BROWSER_PROCESS,),
        daemon=True,
    )
    watcher.start()
    return True


def _terminate_browser(process):
    if process.poll() is not None:
        return

    if sys.platform.startswith("linux"):
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            process.terminate()
    elif sys.platform.startswith("win"):
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        process.terminate()

    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        if sys.platform.startswith("linux"):
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (OSError, ProcessLookupError):
                process.kill()
        else:
            process.kill()


def stop_eontimer():
    global _SERVER, _SERVER_THREAD, _BROWSER_PROCESS, _BROWSER_PROFILE
    global _EXIT_CALLBACK, _STOP_REQUESTED

    _STOP_REQUESTED = True

    if _BROWSER_PROCESS is not None:
        _terminate_browser(_BROWSER_PROCESS)
        _BROWSER_PROCESS = None

    if _SERVER is not None:
        _SERVER.shutdown()
        _SERVER.server_close()
        _SERVER = None

    if _SERVER_THREAD is not None:
        _SERVER_THREAD.join(timeout=1)
        _SERVER_THREAD = None

    if _BROWSER_PROFILE is not None:
        shutil.rmtree(_BROWSER_PROFILE, ignore_errors=True)
        _BROWSER_PROFILE = None

    _EXIT_CALLBACK = None
    _set_status("EonTimer closed.")
