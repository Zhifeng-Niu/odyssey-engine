---
description: "Pause active Odyssey mission temporarily (state preserved, can resume)"
allowed-tools:
  - "Bash(test -f .claude/odyssey.local.md:*)"
  - "Bash(cat .claude/odyssey.local.md:*)"
  - "Read"
  - "Edit"
---

# /odyssey-pause — Pause Mission

Temporarily pauses an active Odyssey mission. State is preserved (MISSION.md, odyssey.jsonl, .claude/odyssey.local.md all retained). The mission can be resumed with `/odyssey --resume` or `/odyssey-resume`.

Unlike `/odyssey-cancel`, pause does NOT remove the state file — it only sets `active: false` so the stop hook allows exit. Resume is a one-line command.

## Steps

1. Check if `.claude/odyssey.local.md` exists
2. If yes:
   - Read it for mission context
   - Set `active: false` in frontmatter:
     ```bash
     sed -i '' 's/^active:.*/active: false/' .claude/odyssey.local.md
     ```
   - Append paused_at timestamp:
     ```bash
     # Add or update paused_at field
     ```
   - Report:
     ```
     ODYSSEY PAUSED
     ===============
     Mission: {title}
     Waypoints completed: {N}
     Best metric: {value}
     Consecutive discards: {X}
     
     State preserved. Resume with: /odyssey --resume
     ```
3. If no active mission:
   - Inform user: "No active Odyssey mission found."

## Difference from /odyssey-cancel

| Action | State File | Resume? | Use When |
|--------|-----------|---------|----------|
| `/odyssey-pause` | Kept (active: false) | Yes, instant | Switching tasks temporarily, want to come back |
| `/odyssey-cancel` | **Removed** | No (must restart) | Done with mission, want clean state |

## Stop Hook Behavior

When `active: false`, `stop-hook.sh` exits with `{"decision":"allow"}` immediately (line 25-27 of hook). This is the existing "no active mission" path — pause reuses it without removing the file.
