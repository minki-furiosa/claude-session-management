---
name: sms-session-new
description: Add a new blank session (no inherited conversation context) to the current sms-tracked branch. Use when the user wants a fresh parallel session on the same branch — without the current session's history. Different from fork, which copies the current context. Runs `sms session-new`.
---

If the user provided a label, capture it. Then run via the Bash tool:

  sms session-new --name "<label-or-empty>"

If no label, omit `--name`.

The command prints the new session's UUID. The new session is registered as a sub on the current branch (not main, no parent_uuid) and appears immediately in Claude Code's `/resume` picker. Tell the user it should now be available there.

This differs from `/sms-fork`: fork copies the current session's conversation; session-new starts blank. Both attach to the current branch's session set, both get the sms SessionStart context when opened.
