#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Reuse an X server that is already running for this user.
if [[ -z "${DISPLAY:-}" && -S /tmp/.X11-unix/X0 ]]; then
    export DISPLAY=:0
    if [[ -z "${XAUTHORITY:-}" && -f "${HOME}/.Xauthority" ]]; then
        export XAUTHORITY="${HOME}/.Xauthority"
    fi
fi

# From a text console, start X and run this script again as its client.
if [[ -z "${DISPLAY:-}" ]]; then
    if ! command -v startx >/dev/null 2>&1; then
        echo "X11 is not installed. Install xserver-xorg, xinit, and openbox." >&2
        exit 1
    fi
    exec startx /bin/bash "${SCRIPT_DIR}/run.sh" -- :0
fi

export SDL_VIDEODRIVER=x11
export SDL_VIDEO_WINDOW_POS=0,0
export PYGAME_BLEND_ALPHA_SDL2=1

window_manager_pid=""
if ! wmctrl -m >/dev/null 2>&1; then
    if command -v openbox >/dev/null 2>&1; then
        openbox --sm-disable &
        window_manager_pid=$!
    elif command -v matchbox-window-manager >/dev/null 2>&1; then
        matchbox-window-manager &
        window_manager_pid=$!
    else
        echo "No X11 window manager found. Install openbox for movable, closable windows." >&2
        exit 1
    fi
fi

cleanup() {
    if [[ -n "${window_manager_pid}" ]]; then
        kill "${window_manager_pid}" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

cd "${SCRIPT_DIR}/app"
"${SCRIPT_DIR}/.venv/bin/python3" main.py
