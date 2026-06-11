#!/usr/bin/env bash
# M1 automated acceptance: drive the real `nava-inject` CLI into a live GTK
# text-entry (zenity) and verify the text actually lands. Exercises both the XTEST
# typing path and the clipboard-paste path end-to-end. Requires X11 + xdotool + zenity.
#
# Usage:  scripts/m1_zenity_acceptance.sh
set -u

INJECT="${INJECT:-nava-inject}"
pass=0; fail=0

need() { command -v "$1" >/dev/null 2>&1 || { echo "MISSING: $1"; exit 3; }; }
need xdotool; need zenity
command -v "$INJECT" >/dev/null 2>&1 || { echo "MISSING: $INJECT (pip install -e .)"; exit 3; }

run_case() {  # $1=title  $2=method  $3=expected text
  local title="$1" method="$2" expect="$3" out wid got
  out="$(mktemp)"
  zenity --entry --title="$title" --text="$title" >"$out" 2>/dev/null &
  local zpid=$!
  # wait for the window to appear (by title), up to ~3s
  wid=""
  for _ in $(seq 1 30); do
    wid="$(xdotool search --name "$title" 2>/dev/null | head -1)"
    [ -n "$wid" ] && break
    sleep 0.1
  done
  if [ -z "$wid" ]; then echo "  [FAIL] $method: zenity window never appeared"; fail=$((fail+1)); kill "$zpid" 2>/dev/null; return; fi
  xdotool windowactivate --sync "$wid" 2>/dev/null
  sleep 0.2
  # live WM_CLASS detection sanity (first case only prints it)
  printf '%s' "$expect" | "$INJECT" --method "$method" >/dev/null 2>&1
  sleep 0.2
  # submit via real XTEST input to the focused entry (XSendEvent is ignored by GTK)
  xdotool windowactivate --sync "$wid" 2>/dev/null
  xdotool key --clearmodifiers Return 2>/dev/null
  wait "$zpid" 2>/dev/null
  got="$(cat "$out")"; rm -f "$out"
  if [ "$got" = "$expect" ]; then
    echo "  [PASS] $method  -> got: '$got'"
    pass=$((pass+1))
  else
    echo "  [FAIL] $method  -> expected: '$expect'  got: '$got'"
    fail=$((fail+1))
  fi
}

echo "== M1 zenity acceptance =="
run_case "nava-m1-type"  type  "hello world"
run_case "nava-m1-paste" paste "pasted text 123"

echo "-- result: $pass passed, $fail failed --"
[ "$fail" -eq 0 ]
