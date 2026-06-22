---
name: sms-fork
description: Fork the current Claude session into a new sub-session on the same branch. Use when the user asks to fork, branch off, or spawn a parallel sub-session. The forked session is registered and visible in the native /resume picker; the current session continues unchanged. Runs `sms fork`.
---

Read any name/label the user passed (free text). Then run via the Bash tool:

  sms fork --name "<label-or-empty>"

If the user did not provide a label, omit `--name`. The command reads `$CLAUDE_CODE_SESSION_ID` (set automatically by Claude Code) to know which session to fork from. Print the new UUID it emits and tell the user it should now be available in the `/resume` picker.
