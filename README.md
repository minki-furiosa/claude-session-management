# sms — Session Management System

Branch-scoped session management for Claude Code. Makes Claude sessions follow
the **branch** they belong to, not the **worktree** they were created in.

Design spec: `docs/superpowers/specs/2026-06-22-sms-branch-scoped-sessions-design.md`

---

## Install

```bash
./install.sh
```

This symlinks `sms` into `~/.local/bin/`, copies the SessionStart hook into
`~/.claude/hooks/`, copies the slash-command skills into `~/.claude/skills/`,
and registers the hook in `~/.claude/settings.json`. Idempotent — safe to
re-run.

Make sure `~/.local/bin` is on `PATH`.

---

## Mental model

Two trees:

- **Branch tree** — git branches, with an explicit "work parent" recorded
  when you create a branch with `sms new`. The work parent often matches git
  ancestry but doesn't have to (you can branch off `main` but tell sms the
  parent is `feature-x` if that's where the work conceptually forks from).
- **Session set per branch** — a flat collection of Claude sessions
  attached to a branch. Exactly one is marked **main**; the rest are
  **subs** (typically forked from the main for parallel review/exploration).

Worktrees are just slots — sessions don't belong to them. When you move a
branch from worktree A to worktree B (via `sms checkout` in B), the
branch's sessions become visible in B's native `/resume` picker.

---

## Daily workflow

### Start a new branch + session

```bash
sms new my-feature --name "draft proposal"
```

Creates `my-feature` (parent = current branch), registers a main session,
and launches `claude` with that session attached. Run from any worktree.

### Fork a parallel sub-session (from inside Claude)

```
/sms-fork "review for memory issues"
```

Inside a running Claude session. Forks the current session into a new sub.
The new session appears in your VSCode `/resume` picker immediately. Open
it from there.

### See what's around

```bash
sms tree                    # branch tree with state, current marked ★
sms tree --all              # include merged + backlog branches
sms sessions                # session set for the current branch
sms sessions --branch foo   # session set for some other branch
```

Or via slash commands inside Claude: `/sms-tree`, `/sms-sessions`.

### Switch branches

```bash
sms checkout other-branch
```

This is `git checkout other-branch` + `sms sync` (rebuilds symlinks so
`/resume` shows the new branch's sessions). **Use this instead of plain
`git checkout`** if you want sms to keep up. If you used plain `git
checkout` (or `git worktree add`, or some other branch-changing command),
run `sms sync` afterward to fix it up.

### Resume a session from a different worktree

In most cases just open VSCode in the right worktree and use the native
`/resume` picker — sms makes sure the right sessions show up there.

If you want to launch from a terminal:

```bash
sms resume <uuid-or-prefix>
```

### Mark branches done

```bash
sms mark-merged              # current branch
sms mark-merged my-feature
sms backlog my-feature       # for "set aside, not merged"
sms activate my-feature      # bring back from merged/backlog
```

Merged and backlog branches are hidden from `sms tree` by default. Pass
`--all` to see them.

### Promote a session to main

```bash
sms set-main <uuid-or-prefix>
```

Or from inside the session: `/sms-set-main`.

---

## Inter-session notes

Every sms-managed branch gets a notes directory at
`<repo>/.git/sms/branches/<branch>/notes/`. It's invisible to git history
and outside any worktree, so it follows the branch wherever it goes.

The SessionStart hook injects the absolute path into every Claude session
on that branch. Sessions can drop handoff documents, findings, todo lists
there for other sessions to pick up. No fixed structure — sessions agree
amongst themselves on naming.

---

## Storage layout (for inspection / repair)

```
<main-repo>/.git/sms/
  tree.json                          # branch tree + session index
  .lock                              # fcntl serialization
  sessions/
    <branch>/
      <uuid>.jsonl                   # canonical session transcript
      <uuid>/tool-results/...        # canonical session subdir (if any)
  branches/
    <branch>/
      notes/                         # inter-session notes (lazy)

~/.claude/projects/<cwd-hash>/
  <uuid>.jsonl  →  symlink to canonical    # only for current branch
  <uuid>/       →  symlink to canonical    # if subdir exists
```

`tree.json` is plain JSON — you can read or edit it if something goes wrong.

---

## What can go wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `/resume` picker doesn't show expected sessions | Symlinks weren't rebuilt after a non-sms branch change | `sms sync` |
| `sms new my-feature` fails saying branch already in tree.json | git branch was deleted but tree.json entry remained | Manually edit `<repo>/.git/sms/tree.json` to remove the orphan entry, then retry |
| Session jsonl missing | Canonical file was deleted | Restore from backup or remove the entry from `tree.json` |
| `sms tree` warns about a cycle | `tree.json` was hand-edited into an inconsistent state | Inspect `<repo>/.git/sms/tree.json` and fix the `parent` field |

---

## Limits (deliberate, for this iteration)

- No automatic adoption of pre-existing branches/sessions. Only branches
  created via `sms new` are in the tree. (`sms adopt` is a future
  extension.)
- No `git branch -m` integration — if you rename a branch via git, the
  tree.json entry stays under the old name. (`sms rename-branch` is a
  future extension.)
- Single repo only — sms doesn't try to span multiple repositories.
- `sms checkout` is the only branch-changing command that auto-syncs.
  Plain `git checkout`, `git switch`, `git worktree add`, VSCode's
  branch picker — all bypass sync. Run `sms sync` after them if needed.

---

## Uninstall

There's no installer flag for this; do it by hand:

```bash
rm ~/.local/bin/sms
rm ~/.claude/hooks/sms-session-start.sh
rm ~/.claude/skills/sms-*.md
# Then edit ~/.claude/settings.json and remove the SessionStart entry pointing at sms-session-start-hook.sh.
```

Per-repo state (`<repo>/.git/sms/`) is independent — keep or remove as you like.
