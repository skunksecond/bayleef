import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eontimer


def test_eontimer_uses_copied_dist_directory():
    assert eontimer._get_eontimer_dir() == (
        Path(eontimer.__file__).resolve().parent / "third_party" / "dist"
    )


def test_exit_controls_are_injected_once():
    source = "<html><head></head><body><div id=\"root\"></div></body></html>"

    result = eontimer._inject_exit_controls(source)
    repeated = eontimer._inject_exit_controls(result)

    assert "button.id = 'bayleef-exit-button'" in result
    assert "fetch('/eontimer/close')" in result
    assert "performance.timeOrigin" in result
    assert "bayleef-js-error" in result
    assert repeated == result


def test_surf_command_enables_fullscreen_javascript_and_inspector():
    command = eontimer._browser_command(
        "/usr/bin/surf",
        "http://127.0.0.1:8000/",
        None,
    )

    assert command == [
        "/usr/bin/surf",
        "-F",
        "-S",
        "-N",
        "http://127.0.0.1:8000/",
    ]


def test_epiphany_command_uses_private_instance_and_isolated_profile():
    command = eontimer._browser_command(
        "/usr/bin/epiphany-browser",
        "http://127.0.0.1:8000/",
        "/tmp/eontimer-profile",
    )

    assert command == [
        "/usr/bin/epiphany-browser",
        "--private-instance",
        "--profile=/tmp/eontimer-profile",
        "http://127.0.0.1:8000/",
    ]


def test_browser_failure_message_includes_last_error_line():
    message = eontimer._browser_failure_message(
        "/usr/bin/epiphany-browser",
        1,
        "first detail\nfinal detail\n",
    )

    assert message == "epiphany-browser exited with code 1: final detail"


def test_surf_is_the_default_browser(monkeypatch):
    monkeypatch.delenv("BAYLEEF_EONTIMER_BROWSER", raising=False)
    monkeypatch.setattr(
        eontimer.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in ("surf", "epiphany-browser") else None,
    )

    assert eontimer._find_browser() == "/usr/bin/surf"


def test_native_gen3_uses_console_frame_rate():
    timer = eontimer.NativeEonTimer(console=eontimer.Console.GBA)
    values = dict(eontimer.DEFAULT_VALUES)

    phases = timer.create_phases(eontimer.TimerMode.GEN3_STANDARD, values)

    assert phases == [5000, timer.to_milliseconds(1000)]


def test_native_gen5_entralink_plus_matches_source_formula():
    timer = eontimer.NativeEonTimer()
    values = dict(eontimer.DEFAULT_VALUES)

    phases = timer.create_phases(eontimer.TimerMode.GEN5_ENTRALINK_PLUS, values)

    assert len(phases) == 3
    assert phases[2] == values["target_advances"] / 0.837148929 * 1000


def test_native_runner_advances_phases_with_monotonic_time():
    timer = eontimer.NativeEonTimer(action_count=0)
    values = dict(eontimer.DEFAULT_VALUES)
    values.update(pre_timer=1000, target_frame=60, gen3_calibration=0)
    timer.start(eontimer.TimerMode.GEN3_STANDARD, values, now_ns=1_000_000_000)

    timer.update(now_ns=2_100_000_000)

    assert timer.phase_index == 1
    assert 90 <= timer.elapsed_ms(now_ns=2_100_000_000) <= 110


def test_native_variable_target_can_be_set_while_running():
    timer = eontimer.NativeEonTimer()
    values = dict(eontimer.DEFAULT_VALUES)
    timer.start(eontimer.TimerMode.GEN3_VARIABLE, values, now_ns=0)

    assert math.isinf(timer.phases[1])
    assert timer.set_variable_target(1200, 25, now_ns=1)
    assert timer.phases[1] == timer.to_milliseconds(1200) + 25


def test_native_gen4_calibration_updates_calibrated_delay():
    timer = eontimer.NativeEonTimer()
    values = dict(eontimer.DEFAULT_VALUES)
    values.update(target_delay=600, calibrated_delay=500, delay_hit=610)

    updates = timer.calibrate(eontimer.TimerMode.GEN4, values)

    assert updates["calibrated_delay"] > values["calibrated_delay"]
