import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eontimer


def test_exit_controls_are_injected_once():
    source = "<html><head></head><body><div id=\"root\"></div></body></html>"

    result = eontimer._inject_exit_controls(source)
    repeated = eontimer._inject_exit_controls(result)

    assert "button.id = 'bayleef-exit-button'" in result
    assert "fetch('/eontimer/close')" in result
    assert repeated == result


def test_surf_command_enables_fullscreen_and_javascript():
    command = eontimer._browser_command(
        "/usr/bin/surf",
        "http://127.0.0.1:8000/",
        None,
    )

    assert command == [
        "/usr/bin/surf",
        "-F",
        "-S",
        "http://127.0.0.1:8000/",
    ]


def test_epiphany_command_uses_application_mode_and_isolated_profile():
    command = eontimer._browser_command(
        "/usr/bin/epiphany-browser",
        "http://127.0.0.1:8000/",
        "/tmp/eontimer-profile",
    )

    assert command == [
        "/usr/bin/epiphany-browser",
        "--application-mode",
        "--profile=/tmp/eontimer-profile",
        "http://127.0.0.1:8000/",
    ]
