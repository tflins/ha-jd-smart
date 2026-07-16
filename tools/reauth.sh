#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${JD_SMART_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/ha-jd-smart}"
VENV_DIR="$STATE_DIR/venv"
CONF_DIR="$STATE_DIR/mitmproxy"
OUTPUT_FILE="${JD_SMART_AUTH_OUTPUT:-$STATE_DIR/jd-smart-auth.json}"
PORT="${JD_SMART_PROXY_PORT:-8081}"
PACKAGE="${JD_SMART_ANDROID_PACKAGE:-com.jd.iots}"
ADDON="$ROOT_DIR/tools/capture_auth.py"
CERT_FILE="$CONF_DIR/mitmproxy-ca-cert.cer"
PHONE_CERT="/sdcard/Download/jd-smart-mitm-ca.cer"
MITMDUMP="$VENV_DIR/bin/mitmdump"

usage() {
  echo "Usage: tools/reauth.sh setup|capture|cleanup"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

ensure_runtime() {
  require_command python3
  require_command adb
  mkdir -p "$STATE_DIR" "$CONF_DIR"
  chmod 700 "$STATE_DIR" "$CONF_DIR"
  if [[ ! -x "$MITMDUMP" ]]; then
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/python" -m pip install "mitmproxy>=12.2,<13"
  fi
}

ensure_device() {
  if [[ "$(adb get-state 2>/dev/null || true)" != "device" ]]; then
    echo "No authorized Android device is connected through ADB." >&2
    exit 1
  fi
}

clear_device_proxy() {
  adb shell settings put global http_proxy :0 >/dev/null 2>&1 || true
  local key
  for key in \
    http_proxy \
    global_http_proxy_host \
    global_http_proxy_port \
    global_http_proxy_exclusion_list \
    global_proxy_pac_url; do
    adb shell settings delete global "$key" >/dev/null 2>&1 || true
  done
}

detect_proxy_host() {
  if [[ -n "${JD_SMART_PROXY_HOST:-}" ]]; then
    echo "$JD_SMART_PROXY_HOST"
    return
  fi

  case "$(uname -s)" in
    Darwin)
      local interface
      interface="$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}')"
      ipconfig getifaddr "$interface"
      ;;
    Linux)
      ip route get 1.1.1.1 | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}'
      ;;
    *)
      echo "Set JD_SMART_PROXY_HOST to the computer IP reachable by the phone." >&2
      exit 1
      ;;
  esac
}

generate_ca() {
  if [[ -f "$CERT_FILE" ]]; then
    return
  fi

  "$MITMDUMP" -q --set "confdir=$CONF_DIR" --listen-host 127.0.0.1 --listen-port "$PORT" &
  local pid=$!
  for _ in {1..50}; do
    [[ -f "$CERT_FILE" ]] && break
    sleep 0.1
  done
  kill "$pid" >/dev/null 2>&1 || true
  wait "$pid" >/dev/null 2>&1 || true
  if [[ ! -f "$CERT_FILE" ]]; then
    echo "Unable to generate the mitmproxy CA certificate." >&2
    exit 1
  fi
}

setup_device() {
  ensure_runtime
  ensure_device
  generate_ca
  adb push "$CERT_FILE" "$PHONE_CERT" >/dev/null
  adb shell am start -a android.settings.SECURITY_SETTINGS >/dev/null 2>&1 || true
  echo "Certificate copied to: $PHONE_CERT"
  echo "Install it as a user CA certificate, then run: tools/reauth.sh capture"
}

copy_output() {
  if command -v pbcopy >/dev/null 2>&1; then
    pbcopy < "$OUTPUT_FILE"
    echo "Capture JSON copied to the clipboard."
  elif command -v xclip >/dev/null 2>&1; then
    xclip -selection clipboard < "$OUTPUT_FILE"
    echo "Capture JSON copied to the clipboard."
  fi
}

capture_auth() {
  ensure_runtime
  ensure_device
  generate_ca

  local proxy_host previous_proxy proxy_pid
  proxy_host="$(detect_proxy_host)"
  previous_proxy="$(adb shell settings get global http_proxy | tr -d '\r')"
  proxy_pid=""

  restore_proxy() {
    if [[ -n "$proxy_pid" ]]; then
      kill "$proxy_pid" >/dev/null 2>&1 || true
      wait "$proxy_pid" >/dev/null 2>&1 || true
    fi
    if [[ -z "$previous_proxy" || "$previous_proxy" == "null" || "$previous_proxy" == ":0" ]]; then
      clear_device_proxy
    else
      adb shell settings put global http_proxy "$previous_proxy" >/dev/null
    fi
  }
  trap restore_proxy EXIT INT TERM

  rm -f "$OUTPUT_FILE"
  JD_SMART_AUTH_OUTPUT="$OUTPUT_FILE" "$MITMDUMP" \
    -q \
    --set "confdir=$CONF_DIR" \
    --listen-host 0.0.0.0 \
    --listen-port "$PORT" \
    -s "$ADDON" &
  proxy_pid=$!

  adb shell settings put global http_proxy "$proxy_host:$PORT" >/dev/null
  adb shell am force-stop "$PACKAGE"
  adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null
  echo "Waiting for JD Smart authentication traffic."
  wait "$proxy_pid"
  proxy_pid=""
  restore_proxy
  trap - EXIT INT TERM

  if [[ ! -s "$OUTPUT_FILE" ]]; then
    echo "No authentication data was captured." >&2
    exit 1
  fi
  chmod 600 "$OUTPUT_FILE"
  copy_output
  echo "Capture JSON saved to: $OUTPUT_FILE"
  echo "In Home Assistant, choose JD Smart > Add device > Import capture JSON."
}

cleanup_device() {
  require_command adb
  ensure_device
  clear_device_proxy
  adb shell rm -f "$PHONE_CERT"
  echo "Proxy cleared and the downloaded certificate file removed."
  echo "Remove the installed user CA certificate from Android settings separately."
}

case "${1:-}" in
  setup)
    setup_device
    ;;
  capture)
    capture_auth
    ;;
  cleanup)
    cleanup_device
    ;;
  *)
    usage
    exit 1
    ;;
esac
