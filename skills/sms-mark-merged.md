---
name: sms-mark-merged
description: Mark the current branch (or a named branch) as merged in the sms tree, hiding it from default `sms tree` listings. Use when the user finishes a branch and wants it out of the active view. Runs `sms mark-merged`.
---

Run via the Bash tool:

  sms mark-merged [branch]

If the user specified a branch, pass it; otherwise default (uses current branch).
