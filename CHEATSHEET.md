# sms — command cheat sheet

## CLI

Run from any worktree's terminal (VSCode integrated terminal counts).

### Create

| Command | Effect |
|---|---|
| `sms new <branch> [--name <label>]` | git checkout -b + register branch in sms tree + register first (main) session + materialize so the VSCode `/resume` picker shows it. Does NOT auto-launch Claude. Pass `--launch` to launch instead. |
| `sms adopt [--name <label>]` | Register the CURRENT (already-existing, non-sms) branch into the tree + create its first session. Sibling of `sms new` for branches you made with plain git. Does not create/switch branches. Registered as a root (parent: none). |
| `sms session-new [--name <label>]` | Add a blank sub-session to the current sms-tracked branch. Independent of the running session (no inherited conversation). |
| `sms fork [--from <uuid>] [--name <label>]` | Fork a session — copy its jsonl to a new UUID, register as a sub on the same branch. With no `--from`, uses `$CLAUDE_CODE_SESSION_ID` (set automatically inside Claude). |

Default `--name` if you omit it: branch name for the first session, `<branch> (2)`, `(3)`, … for subsequent ones.

### Navigate

| Command | Effect |
|---|---|
| `sms tree` | Branch tree. `★` = current branch. State `[merged]` / `[backlog]` hidden by default. |
| `sms tree --all` | Include merged + backlog branches. |
| `sms sessions` | Sessions on the current branch. `*` = main. |
| `sms sessions --branch <b>` | Sessions on a specific branch. |
| `sms checkout <branch>` | git checkout + `sms sync` (rebuild symlinks). **Use this instead of plain `git checkout`** so `/resume` follows. |
| `sms sync` | Manually rebuild symlinks for current branch. Safety net for branch changes that bypassed `sms checkout` (`git worktree add`, VSCode branch picker, etc). |
| `sms resume <uuid-or-prefix>` | Fallback for opening a session from a terminal. Usually you'll just click in VSCode `/resume` picker. |

### Modify / clean up

| Command | Effect |
|---|---|
| `sms set-main <uuid-or-prefix>` | Mark a session as the branch's main. |
| `sms mark-merged [branch]` | Branch done — hide from default tree. |
| `sms backlog [branch]` | Branch paused — hide. |
| `sms activate [branch]` | Bring back to active. |
| `sms session-delete <uuid-or-prefix>` | Delete session: canonical jsonl, symlinks across all worktrees, file-history/session-env caches, tree.json entry. Refuses to delete the currently-running session. |

### Internal (only useful for debugging)

| Command | Effect |
|---|---|
| `sms debug-paths` | Dump resolved paths for current cwd. |
| `sms debug-tree {init,add-branch,add-session,set-main,set-state}` | Direct tree.json mutations. |
| `sms debug-symlink {make,remove,scan}` | Direct symlink ops. |
| `sms hook session-start [--cwd PATH]` | Driver for the SessionStart hook (emits the context block). |

---

## Slash skills (from inside a Claude session)

Each `/sms-*` skill shells out to the corresponding CLI command.

| Skill | Wraps |
|---|---|
| `/sms-tree` | `sms tree` |
| `/sms-sessions` | `sms sessions` (current branch) |
| `/sms-fork [name]` | `sms fork --name "<label>"` — reads `$CLAUDE_CODE_SESSION_ID` for the parent |
| `/sms-adopt [name]` | `sms adopt --name "<label>"` — register the current existing branch |
| `/sms-session-new [name]` | `sms session-new --name "<label>"` |
| `/sms-set-main` | `sms set-main "$CLAUDE_CODE_SESSION_ID"` — promote the current session |
| `/sms-mark-merged [branch]` | `sms mark-merged …` |
| `/sms-backlog [branch]` | `sms backlog …` |
| `/sms-session-delete <uuid>` | `sms session-delete …` |

`sms new`, `checkout`, `sync`, and `resume` are intentionally not slash skills — they involve git ops, symlink rewrites of the current worktree, or launching new processes, none of which compose cleanly from inside an existing session. Use the integrated terminal instead.

---

## Storage layout (for debugging)

```
<main-repo>/.git/sms/
  tree.json                          # branch tree + session index
  .lock                              # fcntl serialization
  sessions/
    <branch>/
      <uuid>.jsonl                   # canonical session transcript
      <uuid>/                        # tool-results subdir (if any)
  branches/
    <branch>/
      notes/                         # inter-session notes (lazy)

~/.claude/projects/<cwd-hash>/
  <uuid>.jsonl  →  symlink to canonical    # only for current branch
  <uuid>/       →  symlink to canonical    # if subdir exists
```

`tree.json` is plain JSON — readable and hand-editable.

The picker's display name comes from a `custom-title` jsonl entry, NOT from `tree.json["branches"][branch]["sessions"][uuid]["name"]` (that is sms-internal). `sms new`/`session-new` pass `--name` to claude (which writes custom-title); `sms fork` writes the line itself after copying.

---

## Hook context (auto-injected at every Claude session start)

For sessions on sms-tracked branches, the SessionStart hook adds to the session prompt:

```
=== sms context ===
Branch: <branch>  (parent: <parent>)
Sessions on this branch: N (M main, K sub)

sms branch memory — durable scratchpad shared by every session on this branch.
  Path: <repo>/.git/sms/branches/<branch>/notes/
  Survives worktree moves (lives in .git, not the working tree).
  Use it for handoffs, findings, todos that other sessions on this branch should pick up.
  Existing files: <list> | (empty — drop markdown files here as needed.)
```

Sessions on non-sms branches see nothing — hook is a silent no-op.

---

## Common workflows

**Start a new line of work:**
```bash
sms new feature-x --name "draft proposal"
# UUID printed. Open VSCode /resume picker (auto-refreshes after ~10s as
# the background materialize finishes). Click the session to start chatting.
```

**Fork a parallel reviewer from inside a session:**
```
/sms-fork "review for memory issues"
```
New session appears in the `/resume` picker. Open in a new tab.

**Move work to a different worktree:**
```bash
cd ~/workspace/wtA
git switch other-branch        # plain git
sms sync                       # → fix up symlinks
# OR equivalently:
sms checkout other-branch      # one-shot
```

**Pick up old branch sessions:**
```bash
sms checkout that-old-branch   # symlinks rebuilt; /resume shows its sessions
```

**Branch is done:**
```bash
sms mark-merged                # current branch
# or
sms mark-merged feature-x
```

**Bad test session needs cleaning:**
```bash
sms session-delete <uuid-or-prefix>
```

---

## Things that can go wrong

| Symptom | Cause | Fix |
|---|---|---|
| `/resume` picker doesn't show a freshly-created session | Materialize step (background `claude --print`) hasn't finished yet | Wait ~10–15 s and refresh the picker (close/reopen, or "Reload Window"). |
| `/resume` picker stale after non-sms branch change | `git checkout` / `worktree add` etc bypassed sms | `sms sync` |
| `/sms-fork` errors "no parent session UUID" | `$CLAUDE_CODE_SESSION_ID` not set in this shell | Pass `--from <uuid>` explicitly, or invoke from inside Claude (where Claude Code sets it automatically). |
| `sms new <branch>` fails "branch already in tree.json" | git branch was deleted but the tree.json entry stayed | Edit `<repo>/.git/sms/tree.json` and delete the orphan entry, or pick a different name. |
| `sms tree` warns "cycle in branch tree" | `tree.json` was hand-edited inconsistently | Inspect and fix the `parent` field for the cycled branches. |
| Canonical jsonl missing for a tree-listed session | Canonical file was deleted out from under us | Restore from backup, or `sms session-delete <uuid>` to drop the orphan record. |
| New skill doesn't appear in the slash menu | Claude session was started before the install | Reload the VSCode window / restart Claude. |

---

## Uninstall

No installer flag — do it by hand:

```bash
rm ~/.local/bin/sms
rm ~/.claude/hooks/sms-session-start.sh
rm -rf ~/.claude/skills/sms-*
# Edit ~/.claude/settings.json and remove the SessionStart entry
# pointing at sms-session-start-hook.sh.
```

Per-repo state (`<repo>/.git/sms/`) is independent — keep or delete as you like.
