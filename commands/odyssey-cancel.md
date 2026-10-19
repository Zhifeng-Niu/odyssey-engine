---
description: "Cancel active Odyssey mission and stop the loop"
allowed-tools:
  - "Bash(test -f .claude/odyssey.local.md:*)"
  - "Bash(sed -i * .claude/odyssey.local.md:*)"
  - "Bash(cat .claude/odyssey.local.md:*)"
  - "Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/odyssey_helper.py summary:*)"
  - "Read"
  - "Edit"
---

# /odyssey-cancel — Cancel Mission

Deactivates the mission state file (the file is kept as an archive so
waypoint history and metrics survive), allowing the agent to exit normally
on the next stop-hook check.

## Steps

1. Check if `.claude/odyssey.local.md` exists
2. If yes and it contains `active: true`:
   - Read it for mission context
   - Archive it — set inactive, never delete:
     ```bash
     sed -i '' 's/^active:.*/active: false/' .claude/odyssey.local.md   # macOS
     sed -i 's/^active:.*/active: false/' .claude/odyssey.local.md      # Linux
     ```
   - Generate a brief cancellation report:
     ```
     ODYSSEY CANCELLED
     =================
     Mission: {title}
     Waypoints completed: {N}
     Best metric: {value}
     Result: CANCELLED BY USER
     ```
3. If no active mission (file missing or `active: false`):
   - Inform the user: "No active Odyssey mission found."
