#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
SMS_SRC="$(pwd)"

BIN_DIR="${HOME}/.local/bin"
HOOK_DIR="${HOME}/.claude/hooks"
SKILL_DIR="${HOME}/.claude/skills"
SETTINGS="${HOME}/.claude/settings.json"

mkdir -p "$BIN_DIR" "$HOOK_DIR" "$SKILL_DIR"

# 1. Symlink the sms binary
ln -sf "$SMS_SRC/sms" "$BIN_DIR/sms"
echo "installed: $BIN_DIR/sms -> $SMS_SRC/sms"

# 2. Install the hook wrapper
cp "$SMS_SRC/sms-session-start-hook.sh" "$HOOK_DIR/sms-session-start.sh"
chmod +x "$HOOK_DIR/sms-session-start.sh"
echo "installed: $HOOK_DIR/sms-session-start.sh"

# 3. Register the hook in settings.json (idempotent: merge or create)
python3 - <<PY
import json
import os
from pathlib import Path

settings_path = Path(os.environ["HOME"]) / ".claude" / "settings.json"
hook_cmd = str(Path(os.environ["HOME"]) / ".claude" / "hooks" / "sms-session-start.sh")

data = {}
if settings_path.exists():
    data = json.loads(settings_path.read_text() or "{}")

hooks = data.setdefault("hooks", {})
ss = hooks.setdefault("SessionStart", [])
# Ensure exactly one entry referencing our wrapper
entry = {"hooks": [{"type": "command", "command": hook_cmd}]}
already = any(
    any(h.get("command") == hook_cmd for h in (group.get("hooks") or []))
    for group in ss if isinstance(group, dict)
)
if not already:
    ss.append(entry)

settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(data, indent=2) + "\n")
print(f"registered SessionStart hook in {settings_path}")
PY

# 4. Install skills (Claude Code expects <name>/SKILL.md, not flat <name>.md)
for f in skills/*.md; do
    name=$(basename "$f" .md)
    dest_dir="$SKILL_DIR/$name"
    # Replace any pre-existing flat .md from older installs.
    rm -f "$SKILL_DIR/$name.md"
    mkdir -p "$dest_dir"
    cp "$f" "$dest_dir/SKILL.md"
    echo "installed: $dest_dir/SKILL.md"
done

echo ""
echo "Done. If $BIN_DIR is not on PATH, add it:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
