---
description: "Show current Odyssey mission status and progress"
allowed-tools:
  - "Bash(python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py summary:*)"
  - "Bash(cat .claude/odyssey.local.md:*)"
  - "Bash(git log:*)"
  - "Bash(git diff:*)"
  - "Read"
---

# /odyssey-status — Mission Status

Reads state files and presents current mission progress.

## Output

1. Read `.claude/odyssey.local.md` for loop state (iteration, orientation, started_at)
2. Read `MISSION.md` for goal, scope, and "What's Been Tried"
3. Run helper summary:
   ```bash
   python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py summary --jsonl odyssey.jsonl
   ```
4. Present:
   - Mission name and goal
   - Current waypoint number
   - Orientation mode
   - Best metric vs baseline
   - Kept/Discarded counts
   - Last 5 waypoints
   - Time elapsed
   - Consecutive discards (if > 0, warn about stuck risk)
