from dataclasses import dataclass, field
from enum import Enum
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

_SERVER = None
_SERVER_THREAD = None
_BROWSER_PROCESS = None
_BROWSER_PROFILE = None
_BROWSER_PROFILE_TEMPORARY = False
_EXIT_CALLBACK = None
_STOP_REQUESTED = False
_STATUS_TEXT = "EonTimer idle."


# The native timer below is a small, UI-independent port of the calculation
# layer in third_party/EonTimerpython.  Keeping it here lets Bayleef use the
# original formulas without importing EonTimer's PySide6 widgets.
class Console(Enum):
    GBA = ("GBA", 59.7275)
    NDS_SLOT1 = ("NDS - Slot 1", 59.8261)
    NDS_SLOT2 = ("NDS - Slot 2", 59.6555)
    DSI = ("DSi", 59.8261)
    THREE_DS = ("3DS", 59.8261)

    def __init__(self, label, fps):
        self.label = label
        self.fps = fps


class TimerMode(Enum):
    GEN3_STANDARD = ("Gen 3", "Standard")
    GEN3_VARIABLE = ("Gen 3", "Variable Target")
    GEN4 = ("Gen 4", "Standard")
    GEN5_STANDARD = ("Gen 5", "Standard")
    GEN5_CGEAR = ("Gen 5", "C-Gear")
    GEN5_ENTRALINK = ("Gen 5", "Entralink")
    GEN5_ENTRALINK_PLUS = ("Gen 5", "Entralink+")

    def __init__(self, generation, label):
        self.generation = generation
        self.label = label


DEFAULT_VALUES = {
    "pre_timer": 5000,
    "target_frame": 1000,
    "gen3_calibration": 0.0,
    "frame_hit": None,
    "target_delay": 1200,
    "target_second": 50,
    "calibrated_delay": 500,
    "calibrated_second": 14,
    "calibration": -95,
    "entralink_calibration": 256,
    "target_advances": 100,
    "frame_calibration": 0.0,
    "delay_hit": None,
    "second_hit": None,
    "advances_hit": None,
}


def _minimum_length(value, minimum=14000):
    while value < minimum:
        value += 60000
    return value


@dataclass
class NativeEonTimer:
    """EonTimer calculations and monotonic phase playback, without a GUI."""

    console: Console = Console.NDS_SLOT1
    minimum_length_ms: int = 14000
    precision_calibration: bool = False
    action_interval_ms: int = 500
    action_count: int = 6
    phases: list[float] = field(default_factory=list)
    phase_index: int = 0
    running: bool = False
    completed: bool = False
    _phase_started_ns: int = 0
    _elapsed_before_phase_ms: float = 0.0
    _fired_actions: set[int] = field(default_factory=set)

    @property
    def frame_ms(self):
        return 1000 / self.console.fps

    def to_milliseconds(self, frames):
        return round(self.frame_ms * frames)

    def to_frames(self, milliseconds):
        return round(milliseconds / self.frame_ms)

    def calibration_to_ms(self, value):
        return float(value) if self.precision_calibration else self.to_milliseconds(value)

    def calibration_to_frames(self, value):
        return round(value) if self.precision_calibration else self.to_frames(value)

    def delay_phases(self, target_delay, target_second, calibration):
        first = _minimum_length(
            target_second * 1000 + calibration + 200 - self.to_milliseconds(target_delay),
            self.minimum_length_ms,
        )
        return [first, self.to_milliseconds(target_delay) - calibration]

    def create_phases(self, mode, values):
        if mode == TimerMode.GEN3_STANDARD:
            return [
                values["pre_timer"],
                self.to_milliseconds(values["target_frame"]) + values["gen3_calibration"],
            ]
        if mode == TimerMode.GEN3_VARIABLE:
            return [values["pre_timer"], math.inf]
        if mode == TimerMode.GEN4:
            calibration = self.to_milliseconds(
                values["calibrated_delay"] - self.to_frames(values["calibrated_second"] * 1000)
            )
            return self.delay_phases(values["target_delay"], values["target_second"], calibration)

        calibration = self.calibration_to_ms(values["calibration"])
        if mode == TimerMode.GEN5_STANDARD:
            return [_minimum_length(values["target_second"] * 1000 + calibration + 200)]

        phases = self.delay_phases(values["target_delay"], values["target_second"], calibration)
        if mode in (TimerMode.GEN5_ENTRALINK, TimerMode.GEN5_ENTRALINK_PLUS):
            phases[0] += 250
            phases[1] -= self.calibration_to_ms(values["entralink_calibration"])
        if mode == TimerMode.GEN5_ENTRALINK_PLUS:
            phases.append(
                values["target_advances"] / 0.837148929 * 1000
                + values["frame_calibration"]
            )
        return phases

    def calibrate(self, mode, values):
        updates = {}
        if mode in (TimerMode.GEN3_STANDARD, TimerMode.GEN3_VARIABLE):
            if values.get("frame_hit") is not None:
                offset = self.to_milliseconds(values["target_frame"] - values["frame_hit"])
                updates["gen3_calibration"] = values["gen3_calibration"] + offset
            return updates

        if mode == TimerMode.GEN4:
            if values.get("delay_hit") is not None and values["delay_hit"] > 0:
                delta = self._delay_calibration(values["target_delay"], values["delay_hit"])
                updates["calibrated_delay"] = values["calibrated_delay"] + self.to_frames(delta)
            return updates

        if mode == TimerMode.GEN5_STANDARD and values.get("second_hit") is not None:
            delta = self._second_calibration(values["target_second"], values["second_hit"])
            updates["calibration"] = values["calibration"] + self.calibration_to_frames(delta)
        elif mode == TimerMode.GEN5_CGEAR and values.get("delay_hit") is not None:
            delta = self._delay_calibration(values["target_delay"], values["delay_hit"])
            updates["calibration"] = values["calibration"] + self.calibration_to_frames(delta)
        elif mode in (TimerMode.GEN5_ENTRALINK, TimerMode.GEN5_ENTRALINK_PLUS):
            if values.get("second_hit") is not None and values["second_hit"] != values["target_second"]:
                delta = self._second_calibration(values["target_second"], values["second_hit"])
                updates["calibration"] = values["calibration"] + self.calibration_to_frames(delta)
            if values.get("delay_hit") is not None and values["delay_hit"] != values["target_delay"]:
                delta = self._delay_calibration(values["target_delay"], values["delay_hit"])
                updates["entralink_calibration"] = (
                    values["entralink_calibration"] + self.calibration_to_frames(delta)
                )
            if (
                mode == TimerMode.GEN5_ENTRALINK_PLUS
                and values.get("advances_hit") is not None
                and values["advances_hit"] != values["target_advances"]
            ):
                updates["frame_calibration"] = values["frame_calibration"] + (
                    (values["target_advances"] - values["advances_hit"]) / 0.837148929 * 1000
                )
        return updates

    def _delay_calibration(self, target, hit):
        delta = self.to_milliseconds(hit) - self.to_milliseconds(target)
        return delta * (0.75 if abs(delta) <= 167 else 1.0)

    @staticmethod
    def _second_calibration(target, hit):
        if hit < target:
            return (target - hit) * 1000 - 500
        if hit > target:
            return (target - hit) * 1000 + 500
        return 0.0

    def start(self, mode, values, now_ns=None):
        phases = self.create_phases(mode, values)
        if not phases or any(phase <= 0 for phase in phases):
            raise ValueError("Timer phases must be greater than zero")
        self.phases = phases
        self.phase_index = 0
        self.running = True
        self.completed = False
        self._elapsed_before_phase_ms = 0.0
        self._phase_started_ns = now_ns if now_ns is not None else time.perf_counter_ns()
        self._fired_actions.clear()

    def stop(self):
        self.running = False

    def set_variable_target(self, target_frame, calibration, now_ns=None):
        if len(self.phases) != 2 or not math.isinf(self.phases[1]):
            return False
        self.phases[1] = self.to_milliseconds(target_frame) + calibration
        if self.phase_index == 1:
            self._phase_started_ns = now_ns if now_ns is not None else time.perf_counter_ns()
            self._elapsed_before_phase_ms = 0.0
            self._fired_actions.clear()
        return True

    def update(self, now_ns=None):
        """Advance playback and return the number of newly due action cues."""
        if not self.running:
            return 0
        now_ns = now_ns if now_ns is not None else time.perf_counter_ns()
        elapsed = self._elapsed_before_phase_ms + (now_ns - self._phase_started_ns) / 1_000_000
        phase = self.phases[self.phase_index]

        while not math.isinf(phase) and elapsed >= phase:
            if self.phase_index + 1 >= len(self.phases):
                self.running = False
                self.completed = True
                self._elapsed_before_phase_ms = phase
                return 1 if 0 not in self._fired_actions else 0
            elapsed -= phase
            self.phase_index += 1
            phase = self.phases[self.phase_index]
            self._phase_started_ns = now_ns
            self._elapsed_before_phase_ms = elapsed
            self._fired_actions.clear()

        due = 0
        remaining = phase - elapsed
        if not math.isinf(remaining):
            for index in range(self.action_count):
                threshold = self.action_interval_ms * index
                if remaining <= threshold and index not in self._fired_actions:
                    self._fired_actions.add(index)
                    due += 1
        return due

    def elapsed_ms(self, now_ns=None):
        if not self.phases:
            return 0.0
        if not self.running:
            return self._elapsed_before_phase_ms
        now_ns = now_ns if now_ns is not None else time.perf_counter_ns()
        return self._elapsed_before_phase_ms + (now_ns - self._phase_started_ns) / 1_000_000

    def remaining_ms(self, now_ns=None):
        if not self.phases:
            return 0.0
        phase = self.phases[self.phase_index]
        if math.isinf(phase):
            return math.inf
        return max(0.0, phase - self.elapsed_ms(now_ns))

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
        return [browser, "-F", "-S", "-N", url]

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
    command = _browser_command(browser, "http://localhost:8000/", _BROWSER_PROFILE)
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
