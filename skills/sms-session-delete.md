---
name: sms-session-delete
description: Delete an sms session entirely — its canonical jsonl, symlinks in all worktrees, UUID-keyed caches (file-history/session-env), and the tree.json entry. Use when the user wants to remove a stale or test session. Destructive; refuses to delete the currently-running session.
---

Run via the Bash tool:

  sms session-delete <uuid-or-prefix>

The command:
- Resolves the UUID via tree.json (prefix match allowed).
- Refuses to delete the currently-running session (would corrupt the live jsonl).
- Removes the canonical session jsonl + optional tool-results subdir.
- Removes any symlinks in `~/.claude/projects/<cwd-hash>/` across all worktrees.
- Removes `~/.claude/file-history/<uuid>/` and `~/.claude/session-env/<uuid>/`.
- Removes the session from tree.json.

This is destructive. Confirm with the user if the session has conversation history they may want to preserve.
