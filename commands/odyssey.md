---
description: "Start or resume an Odyssey Engine autonomous iteration mission"
allowed-tools:
  - "Bash(bash $CLAUDE_PLUGIN_ROOT/scripts/setup-odyssey.sh:*)"
  - "Bash(python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py:*)"
  - "Bash(git checkout:*)"
  - "Bash(git add:*)"
  - "Bash(git commit:*)"
  - "Bash(git reset:*)"
  - "Bash(git checkout -b:*)"
  - "Read"
  - "Write"
  - "Edit"
  - "Glob"
  - "Grep"
---

# /odyssey — Start or Resume Mission

## Arguments

```
/odyssey PROMPT [--orientation engineer|creative|production] [--max-iterations N] [--time-budget 30m|2h] [--completion-promise TEXT]
/odyssey --resume
/odyssey --mission-file PATH
```

## Behavior

### New Mission

1. Run the setup script to initialize:
   ```bash
   bash $CLAUDE_PLUGIN_ROOT/scripts/setup-odyssey.sh "PROMPT" --orientation ORIENTATION --max-iterations N
   ```

2. The setup script will:
   - Auto-detect project type
   - Create `MISSION.md` from template (or copy from `--mission-file`)
   - Create expedition branch `odyssey/{slug}-{date}`
   - Initialize `odyssey.jsonl` with config header
   - Create `.claude/odyssey.local.md` state file
   - Commit state files

3. After setup, begin the Odyssey loop following the SKILL.md loop procedure.

4. The stop hook will keep the loop running until:
   - Completion promise is fulfilled
   - Max iterations reached
   - Time budget exceeded
   - User runs `/odyssey-cancel`

### Resume Mission

1. Check for `.claude/odyssey.local.md` — if it exists, a mission is active
2. Read `MISSION.md` for full context
3. Read `odyssey.jsonl` for experiment history
4. Continue the loop from the last waypoint

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
