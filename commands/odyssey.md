---
description: "Start or resume an Odyssey Engine autonomous iteration mission"
allowed-tools:
  - "Bash(bash $CLAUDE_PLUGIN_ROOT/scripts/setup-odyssey.sh:*)"
  - "Bash(python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py:*)"
  - "Bash(bash $CLAUDE_PLUGIN_ROOT/scripts/sync-cache.sh:*)"
  - "Bash(git checkout:*)"
  - "Bash(git add:*)"
  - "Bash(git commit:*)"
  - "Bash(git reset:*)"
  - "Bash(git checkout -b:*)"
  - "Bash(git log:*)"
  - "Bash(git diff:*)"
  - "Bash(git status:*)"
  - "Bash(git branch:*)"
  - "Bash(cat .claude/odyssey.local.md:*)"
  - "Bash(test -f .claude/odyssey.local.md:*)"
  - "Read"
  - "Write"
  - "Edit"
  - "Glob"
  - "Grep"
---

# /odyssey — Start or Resume Mission

## Arguments

```
/odyssey PROMPT [--orientation engineer|creative|production] [--time-budget 30m|2h] [--completion-promise TEXT]
/odyssey --resume
/odyssey --mission-file PATH
```

Do NOT pass --max-iterations. The loop runs until convergence is detected (diminishing returns across waypoints) or the user interrupts with /odyssey-cancel.

## Behavior

### New Mission

1. Run the setup script to initialize:
   ```bash
   bash $CLAUDE_PLUGIN_ROOT/scripts/setup-odyssey.sh "PROMPT" --orientation ORIENTATION
   ```
   Do NOT add --max-iterations. The loop stops by convergence detection, not a fixed count.

2. The setup script will:
   - Auto-detect project type
   - Create `MISSION.md` from template (or copy from `--mission-file`)
   - Create expedition branch `odyssey/{slug}-{date}`
   - Initialize `odyssey.jsonl` with config header
   - Create `.claude/odyssey.local.md` state file
   - Commit state files

3. After setup, begin the Odyssey loop following the SKILL.md loop procedure.

4. The stop hook will keep the loop running until:
   - Convergence detected (diminishing returns, exhausted backlog, agent self-assesses no further meaningful improvement)
   - Completion promise is fulfilled
   - Time budget exceeded
   - Stuck (10 consecutive discards)
   - User runs `/odyssey-cancel`

### Resume Mission

1. Check for `.claude/odyssey.local.md` — if it exists, a mission is active
2. Read `MISSION.md` for full context
3. Read `odyssey.jsonl` for experiment history
4. Continue the loop from the last waypoint by following the Re-Entry Procedure in SKILL.md

### Stop Hook Re-Entry

When the stop hook blocks exit and CC continues, it receives a `systemMessage` with:
- Current waypoint number and orientation
- 8-step execution instructions (checkpoint → read → pick → act → verify → decide → record → recap)
- Mission context from MISSION.md

Follow those instructions exactly. Do NOT ask for permission. Do NOT stop between waypoints.

### After Each Waypoint

1. Update `MISSION.md` frontmatter and "What's Been Tried" sections
2. Append to `odyssey.jsonl` via helper:
   ```bash
   python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py log --jsonl odyssey.jsonl --run N --commit SHA --metric VALUE --status keep/discard --description "what was tried"
   ```
3. Commit state files
4. Continue to next waypoint (stop hook will prevent exit)

### When Loop Stops

1. Generate final report
2. Clean up `.claude/odyssey.local.md`
3. Summarize key changes and metric improvement
