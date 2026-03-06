#!/usr/bin/env bash
set -euo pipefail

PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "${pid}" 2>/dev/null || true
  done
}

trap cleanup EXIT INT TERM

if [[ "${HANDOFF_ENABLED:-true}" == "true" ]]; then
  export DISPLAY="${DISPLAY:-:99}"
  Xvfb "${DISPLAY}" -screen 0 1920x1080x24 -ac +extension RANDR &
  PIDS+=($!)
  sleep 1

  x11vnc -display "${DISPLAY}" -forever -shared -rfbport 5900 -nopw >/tmp/x11vnc.log 2>&1 &
  PIDS+=($!)

  websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/tmp/novnc.log 2>&1 &
  PIDS+=($!)
fi

python -m uvicorn main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --log-level "$(echo "${LOG_LEVEL:-INFO}" | tr '[:upper:]' '[:lower:]')" &
APP_PID=$!
PIDS+=("${APP_PID}")

wait "${APP_PID}"
