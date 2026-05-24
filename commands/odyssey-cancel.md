---
description: "Cancel active Odyssey mission and stop the loop"
allowed-tools:
  - "Bash(test -f .claude/odyssey.local.md:*)"
  - "Bash(rm .claude/odyssey.local.md)"
  - "Read"
---

# /odyssey-cancel — Cancel Mission

Removes the stop hook state file, allowing the agent to exit normally on the next iteration.

## Steps

1. Check if `.claude/odyssey.local.md` exists
2. If yes:
   - Read it for mission context
   - Remove it: `rm .claude/odyssey.local.md`
   - Generate a brief cancellation report:
     ```
     ODYSSEY CANCELLED
     =================
     Mission: {title}
     Waypoints completed: {N}
     Best metric: {value}
     Result: CANCELLED BY USER
     ```
3. If no active mission:
   - Inform the user: "No active Odyssey mission found."
