# Loop Procedures — Step-by-Step Execution

Detailed execution flows for every entry point into the Odyssey loop. Read this when you need the *how*, not the *what*. For strategy and decision criteria, see [compass-strategies.md](compass-strategies.md). For verification details, see [verification-patterns.md](verification-patterns.md).

## Three Entry Points

| Entry | Trigger | First Action |
|-------|---------|--------------|
| New mission | `/odyssey "goal"` | Run `setup-odyssey.sh` |
| Resume | `/odyssey --resume` | Read `.claude/odyssey.local.md` |
| Stop-hook re-entry | Hook fires after each waypoint | Read MISSION.md "What's Been Tried" |

## Entry 1: New Mission

```
1. User invokes /odyssey "GOAL" [--orientation X] [--time-budget Y]
2. CC runs:
   bash $CLAUDE_PLUGIN_ROOT/scripts/setup-odyssey.sh "GOAL" --orientation X
3. setup-odyssey.sh performs:
   a. Pre-flight checks (no active mission, prompt provided, git repo)
   b. Project auto-detection via odyssey_helper.py detect
   c. Generate MISSION.md from inline template
   d. Create expedition branch odyssey/{timestamp}
   e. Initialize odyssey.jsonl with config header
   f. Create .claude/odyssey.local.md (stop-hook state)
   g. Commit state files
4. CC starts the loop with Waypoint 1 (see "Single Waypoint" below)
```

### Optional Flags

| Flag | Effect |
|------|--------|
| `--orientation engineer\|creative\|production` | Strategy selector (default: engineer) |
| `--time-budget 30m\|2h` | Hard time cap; auto-deactivates when exceeded |
| `--completion-promise TEXT` | Loop stops when output contains `<promise>{TEXT}</promise>` |
| `--mission-file PATH` | Use existing mission spec instead of generating from prompt |

## Entry 2: Resume

```
1. User invokes /odyssey --resume
2. CC checks: .claude/odyssey.local.md exists?
   - No  → "No active Odyssey mission found."
   - Yes → continue
3. Read state file for orientation, iteration, consecutive_discards
4. Read MISSION.md (full)
5. Read odyssey.jsonl (last 5 entries for recent context)
6. Continue from next waypoint (see "Single Waypoint" below)
```

## Entry 3: Stop-Hook Re-Entry

The stop hook fires after every CC turn while a mission is active. The hook's `systemMessage` provides:
- Current waypoint number
- Orientation mode
- Discard count
- Mission context (first 80 lines of MISSION.md)

CC then executes the **Single Waypoint** procedure below.

## Single Waypoint (the inner loop)

Every waypoint — whether the first or the fiftieth — follows these 8 steps in order. Do not skip. Do not reorder.

### Step 1: CHECKPOINT

```bash
git add -A && git commit -m "waypoint-{N}: checkpoint"
```

- Always commit current state *before* making changes
- If working in a non-git directory, skip but note in waypoint log
- This is the rollback point for discards

### Step 2: READ

- Read `MISSION.md` "What's Been Tried" — **never repeat a dead end**
- Read `odyssey.jsonl` last 3 entries — recent context
- Read `.claude/odyssey.local.md` — discard count, iteration count

**Convergence check** (mandatory before picking next hypothesis):
- Last 3+ waypoints show diminishing returns (metric delta < threshold)?
- Ideas Backlog exhausted (no more unchecked items)?
- Self-assessment: "further iterations unlikely to produce meaningful change"?

If all three are true → output `<converged/>` on a line by itself → stop hook will deactivate and exit.

### Step 3: COMPASS (pick one hypothesis)

Selection rules by orientation:

| Orientation | Selection Rule |
|-------------|----------------|
| engineer | Highest-confidence item from Ideas Backlog; smallest blast radius |
| creative | Most novel approach divergent from last 3 waypoints; bold structural changes OK |
| production | Smallest change likely to improve metric; ship-ready at every step |

**One hypothesis per waypoint.** If you have two ideas, pick one and queue the other.

### Step 4: ACT

- Modify files (write/edit)
- Run any setup commands (install deps, migrate, etc.)
- Keep changes focused — one logical change per waypoint

### Step 5: VERIFY (4-layer pipeline)

Run layers in order. Stop at first failure.

| Layer | Command Example | Failure Action |
|-------|-----------------|----------------|
| 0 Syntax | `python3 -c "import ast; ast.parse(open(f).read())"` | Skip to Step 7 DISCARD |
| 1 Guard | `pytest --tb=short -q` | Skip to Step 7 DISCARD + revert |
| 2 Metric | `bash odyssey.sh` → captures number | Compare to best, decide in Step 7 |
| 3 Quality | bundle size, lint, coverage | Log warning, do not force discard |

For layer 2, use the helper to evaluate:
```bash
python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py evaluate \
  --jsonl odyssey.jsonl --metric NEW_VALUE
```

Returns: `{"improved": true, "previous_best": 320.5, "new_value": 245.1, "delta": -75.4}`

### Step 6: DECIDE

Apply the orientation's decision matrix (see [compass-strategies.md](compass-strategies.md)).

**KEEP** conditions (engineer default):
- All guards pass
- Metric improved OR same with simpler code

**DISCARD** conditions:
- Any guard failed
- Metric worse
- Same metric with more complexity

### Step 7: RECORD outcome

#### If KEEP:
```bash
# 1. Commit the change
git add -A && git commit -m "waypoint-{N}: KEEP — {description}"

# 2. Log to JSONL
python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py log \
  --jsonl odyssey.jsonl --run {N} --commit $(git rev-parse --short HEAD) \
  --metric {VALUE} --status keep --description "{what was tried}"

# 3. Update MISSION.md:
#    - Add to "Wins" section
#    - Update "Current Best" with new metric
#    - Update frontmatter: best_metric, total_waypoints

# 4. Reset consecutive_discards to 0
# Use the helper reset command (added in v1.1):
python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py reset-discards
```

#### If DISCARD:
```bash
# 1. Revert to checkpoint
git reset --hard HEAD~1

# 2. Log to JSONL
python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py log \
  --jsonl odyssey.jsonl --run {N} \
  --status discard --description "{what was tried}" \
  --metric null

# 3. Update MISSION.md:
#    - Add to "Dead Ends" section
#    - Update frontmatter: total_waypoints, consecutive_discards (+1)
```

### Step 8: RECAP & CONTINUE

- Output a one-line recap: `waypoint-{N}: KEEP/DISCARD — {description} (metric: X→Y)`
- **DO NOT stop. DO NOT ask for permission.**
- The stop hook will re-fire automatically and trigger the next waypoint

## Special Procedures

### Creative Mode: Sling (Goliath Pattern)

When the mission seems blocked by a "giant":

```
1. Launch odyssey-explorer agent for cross-pollination
   "Find 3-5 diverse approaches to {problem}, ranked by novelty"
2. Rank approaches by novelty (NOT expected performance)
3. Pick the most unexpected plausible one
4. Execute as a single waypoint
5. Critic evaluation: if result contradicts hypothesis → log as Surprise
```

### Production Mode: Regression Sweep

After every KEEP in production mode:

```bash
# Run full test suite (not just primary guard)
{full_test_command}

# Check for new warnings
{lint_command} | diff against baseline
```

Any new warning triggers a follow-up waypoint to clean up.

### Stuck Recovery (10 consecutive discards)

The stop hook injects a `STUCK` system message. Options:

1. **Switch orientation**: `/odyssey --orientation creative` (if currently engineer)
2. **Broaden scope**: edit MISSION.md Scope section to allow more files
3. **Narrow scope**: edit MISSION.md Goal to be more specific
4. **Cancel**: `/odyssey-cancel`
5. **Force exit**: output `<converged/>`

Recommended: try option 1 first (creative mode unlocks divergence), then 2 or 3 if still stuck.

## File Update Checklist (per waypoint)

| File | When KEEP | When DISCARD |
|------|-----------|--------------|
| `odyssey.jsonl` | Append keep entry | Append discard entry |
| `MISSION.md` frontmatter | Update best_metric, total_waypoints, reset consecutive_discards | Update total_waypoints, increment consecutive_discards |
| `MISSION.md` Wins/Dead Ends | Add to Wins | Add to Dead Ends |
| `MISSION.md` Current Best | Update if metric improved | No change |
| `MISSION.md` Ideas Backlog | Mark item [x] tried | Mark item [x] tried (abandoned) |
| `.claude/odyssey.local.md` | iteration += 1, consecutive_discards = 0 | iteration += 1, consecutive_discards += 1 |
| Git | New commit | Reset to checkpoint |

## When Loop Stops

The loop terminates when any of these conditions fires:

| Condition | How Detected | Cleanup |
|-----------|--------------|---------|
| Converged | Agent outputs `<converged/>` | Stop hook sets active: false |
| MISSION.md status: complete | Stop hook checks frontmatter | Stop hook deactivates |
| Completion promise | Output contains `<promise>{TEXT}</promise>` | Stop hook deactivates |
| Time budget exceeded | Stop hook compares elapsed vs budget | Stop hook deactivates |
| Stuck (10 discards) | Stop hook checks consecutive_discards | Stop hook injects STUCK message |
| User cancel | `/odyssey-cancel` removes state file | Next hook exit allowed |

After termination, CC produces the final report (see [SKILL.md](../SKILL.md) "Final Report" section).
