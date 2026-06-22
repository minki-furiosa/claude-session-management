#!/usr/bin/env bash
# sms SessionStart hook for Claude Code.
# Reads JSON from stdin (Claude's hook protocol), extracts the project dir,
# runs `sms hook session-start --cwd <dir>`, and emits the result as additional_context.
set -euo pipefail

SMS="${SMS_BIN:-sms}"

# Read stdin JSON (best-effort). Claude provides `cwd` in the JSON payload.
input=$(cat || true)
project_dir=""
if [[ -n "$input" ]]; then
  project_dir=$(printf '%s' "$input" | python3 -c "import sys, json; d=json.loads(sys.stdin.read() or '{}'); print(d.get('cwd',''))" 2>/dev/null || true)
fi
if [[ -z "$project_dir" ]]; then
  project_dir="$PWD"
fi

ctx=$("$SMS" hook session-start --cwd "$project_dir" 2>/dev/null || true)
if [[ -z "$ctx" ]]; then
  # Nothing to inject — emit empty hookSpecificOutput
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}\n'
  exit 0
fi

python3 -c "
import json, sys
ctx = sys.stdin.read()
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': ctx}}))
" <<<"$ctx"
