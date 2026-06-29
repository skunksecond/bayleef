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
_BROWSER_PROFILE_TEMPORARY = False
_EXIT_CALLBACK = None
_STOP_REQUESTED = False
_STATUS_TEXT = "EonTimer idle."

_EXIT_STYLE = """
<style id="bayleef-exit-style">
  #bayleef-exit-button {
    position: fixed;
    top: 8px;
    right: 8px;
    z-index: 2147483647;
    border: 1px solid #fff;
    background: #101010;
    color: #fff;
    padding: 8px 10px;
    font: 700 13px sans-serif;
    cursor: pointer;
  }
</style>
"""

_COMPAT_SCRIPT = """
<script id="bayleef-compat-script">
(() => {
  if (!Number.isFinite(performance.timeOrigin)) {
    const timeOrigin = Date.now() - performance.now();
    try {
      Object.defineProperty(performance, 'timeOrigin', { value: timeOrigin });
    } catch (error) {
      performance.timeOrigin = timeOrigin;
    }
  }

  const showError = message => {
    let banner = document.getElementById('bayleef-js-error');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'bayleef-js-error';
      banner.style.cssText = [
        'position:fixed', 'left:8px', 'right:8px', 'bottom:8px',
        'z-index:2147483647', 'padding:8px', 'background:#7f1d1d',
        'color:white', 'font:13px sans-serif', 'white-space:pre-wrap'
      ].join(';');
      document.documentElement.appendChild(banner);
    }
    banner.textContent = 'EonTimer JavaScript error: ' + message;
  };

  window.addEventListener('error', event => showError(event.message || 'Unknown error'));
  window.addEventListener('unhandledrejection', event => {
    const reason = event.reason;
    showError(reason && (reason.stack || reason.message) || String(reason));
  });
})();
</script>
"""

_EXIT_SCRIPT = """
<script id="bayleef-exit-script">
(() => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(registrations => {
      registrations.forEach(registration => registration.unregister());
    });
  }
  const button = document.createElement('button');
  button.id = 'bayleef-exit-button';
  button.type = 'button';
  button.textContent = 'Return to menu';
  button.addEventListener('click', async () => {
    button.disabled = true;
    button.textContent = 'Closing...';
    try {
      await fetch('/eontimer/close');
    } catch (error) {
      button.disabled = false;
      button.textContent = 'Return to menu';
    }
  });
  document.body.appendChild(button);
})();
</script>
"""


def _inject_exit_controls(html: str) -> str:
    if 'id="bayleef-exit-script"' in html:
        return html
    html = html.replace("</head>", f"{_EXIT_STYLE}{_COMPAT_SCRIPT}</head>", 1)
    return html.replace("</body>", f"{_EXIT_SCRIPT}</body>", 1)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def translate_path(self, path):
        # 1. Strip the '/EonTimer' prefix from the URL path if present
        if path.startswith('/EonTimer'):
            path = path.replace('/EonTimer', '', 1)

        # 2. Let the standard SimpleHTTPRequestHandler handle the rest
        return super().translate_path(path)


class EonTimerHandler(QuietHandler):
    def do_GET(self):
        if self.path.startswith("/eontimer/close"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"closing")
            threading.Thread(target=request_exit, daemon=True).start()
            return

        request_path = self.path.split("?", 1)[0]
        if request_path in ("/registerSW.js", "/EonTimer/registerSW.js"):
            self._disable_service_worker()
            return
        if request_path in ("/", "/index.html", "/EonTimer/", "/EonTimer/index.html"):
            self._serve_index_with_exit()
            return

        super().do_GET()

    def _serve_index_with_exit(self):
        index_path = Path(self.directory) / "index.html"
        try:
            html = index_path.read_text(encoding="utf-8")
        except OSError:
            self.send_error(404, "EonTimer index not found")
            return

        content = _inject_exit_controls(html).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _disable_service_worker(self):
        content = (
            "navigator.serviceWorker.getRegistrations()"
            ".then(items => items.forEach(item => item.unregister()));"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def get_status_text() -> str:
    return _STATUS_TEXT


def _set_status(message: str):
    global _STATUS_TEXT
    _STATUS_TEXT = message


def _get_eontimer_dir() -> Path:
    return Path(__file__).resolve().parent / "third_party" / "dist"


def _find_browser() -> str | None:
    epiphany_names = ("epiphany-browser", "epiphany")
    preference = os.environ.get("BAYLEEF_EONTIMER_BROWSER", "surf").strip()
    if preference and preference not in (*epiphany_names, "surf", "auto"):
        explicit_browser = shutil.which(preference)
        if explicit_browser or Path(preference).is_file():
            return explicit_browser or preference

    if preference == "surf":
        names = ("surf", *epiphany_names)
    elif preference == "epiphany":
        names = ("epiphany", "epiphany-browser", "surf")
    else:
        names = (*epiphany_names, "surf")
    for name in names:
        executable = shutil.which(name)
        if executable:
            return executable
    return None


def _create_browser_profile() -> tuple[str, bool]:
    profile = Path.home() / ".cache" / "bayleef" / "eontimer-epiphany"
    try:
        profile.mkdir(parents=True, exist_ok=True)
        return str(profile), False
    except OSError:
        return tempfile.mkdtemp(prefix="bayleef-eontimer-"), True


def _browser_command(browser: str, url: str, profile_dir: str | None) -> list[str]:
    if Path(browser).name == "surf":
        return [browser, "-F", "-S", url]

    if profile_dir is None:
        raise ValueError("Epiphany requires an isolated profile directory")

    return [
        browser,
        "--private-instance",
        f"--profile={profile_dir}",
        url,
    ]


def _browser_failure_message(browser: str, return_code: int, stderr: str) -> str:
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    detail = lines[-1] if lines else "No error details were reported."
    with open("crash_details.txt", "w") as file:
        file.write(detail)
    return f"{Path(browser).name} exited with code {return_code}: {detail}"


def _watch_browser_process(process, browser):
    stderr = process.stderr.read() if process.stderr is not None else ""
    return_code = process.wait()
    if _BROWSER_PROCESS is not process or _STOP_REQUESTED:
        return

    if return_code != 0:
        _set_status(_browser_failure_message(browser, return_code, stderr))
        return

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
    global _BROWSER_PROFILE_TEMPORARY, _EXIT_CALLBACK, _STOP_REQUESTED

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

    browser = _find_browser()
    if not browser:
        _set_status("No browser found. Install Surf, or epiphany-browser as a fallback.")
        return False

    handler = partial(EonTimerHandler, directory=str(eontimer_dir))
    try:
        _SERVER = ThreadingHTTPServer(("127.0.0.1", 8000), handler)
    except OSError as error:
        _set_status(f"Could not start EonTimer server on port 8000: {error}")
        return False

    _SERVER_THREAD = threading.Thread(target=_SERVER.serve_forever, daemon=True)
    _SERVER_THREAD.start()

    if Path(browser).name != "surf":
        _BROWSER_PROFILE, _BROWSER_PROFILE_TEMPORARY = _create_browser_profile()
    command = _browser_command(browser, "http://127.0.0.1:8000/", _BROWSER_PROFILE)
    popen_options = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
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
        args=(_BROWSER_PROCESS, browser),
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
    global _BROWSER_PROFILE_TEMPORARY, _EXIT_CALLBACK, _STOP_REQUESTED

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

    if _BROWSER_PROFILE is not None and _BROWSER_PROFILE_TEMPORARY:
        shutil.rmtree(_BROWSER_PROFILE, ignore_errors=True)
    _BROWSER_PROFILE = None
    _BROWSER_PROFILE_TEMPORARY = False

    _EXIT_CALLBACK = None
    _set_status("EonTimer closed.")
