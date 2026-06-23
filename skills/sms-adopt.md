---
name: sms-adopt
description: Register the current (already-existing, non-sms) git branch into the sms tree and create its first session. Use when the user wants to start using sms on a branch they created with plain git (not `sms new`). Sibling of `sms new` for pre-existing branches. Runs `sms adopt`.
---

If the user provided a label, capture it. Then run via the Bash tool:

  sms adopt --name "<label-or-empty>"

If no label, omit `--name`.

The command registers the currently checked-out branch into the sms tree as
a root (parent: none), creates its first main session, and materializes it so
it appears in the `/resume` picker. It does NOT create or switch git branches
— it adopts whatever branch is currently checked out.

Errors if the branch is already sms-tracked (use `sms session-new` to add
more sessions) or if HEAD is detached.
