---
name: sms-sessions
description: List the Claude sessions associated with the current branch (the branch's session set). Use when the user asks "what sessions are on this branch", "show my sessions", or wants to find a sibling session. Runs `sms sessions`.
---

Run `sms sessions` via the Bash tool and print the output. If the user names a different branch, pass `--branch <name>`.

Output rows: `* <short-uuid> <created> <name>` (`*` = the branch's main).
