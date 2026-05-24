---
name: odyssey
description: >
  Autonomous iteration engine with three orientations (engineer/creative/production).
  Fuses autoresearch metric-driven experiments, gaggle checkpoint/verify/rollback,
  and ralph-loop continuous execution. Use when: iterating on a task, optimizing a metric,
  exploring solutions autonomously, running experiment loops, hardening code for production,
  or when user says "iterate", "optimize", "explore", "keep improving", "run experiments",
  "autoresearch", or "odyssey". Supports MISSION.md task definition, JSONL experiment tracking,
  git branch isolation, stop-hook loops, project auto-detection, and completion promises.
  Named for the Odyssey — a journey of encounters with giants, each requiring a different strategy.
---

# Odyssey Engine

A universal autonomous iteration engine that adapts its strategy to the task. Three orientations, one loop.

**Inspired by**: autoresearch (metric-driven), gaggle-iterate (checkpoint/verify/rollback), ralph-loop (continuous execution). Named for the Odyssey — every mission is a journey with giants to face.

## When to Use

- User says "iterate on this", "optimize X", "explore approaches", "keep improving until it works"
- A task requires multiple attempts with measurable progress
- The solution path is unknown (creative) or must be production-ready (production)
- Running autonomous experiment loops overnight

## Quick Start

```
/odyssey "Reduce API latency below 200ms" --orientation production --max-iterations 20
/odyssey "Find unconventional layout approaches" --orientation creative
/odyssey --resume
```

## The Loop

```
WAYPOINT = 0
LOOP:

  WAYPOINT += 1

  # 1. CHECKPOINT — save current state
  git add -A && git commit -m "waypoint-{N}: checkpoint"

  # 2. COMPASS — choose next approach based on orientation
  ## Read MISSION.md "What's Been Tried" to avoid repeating failures
  ## Select next hypothesis from Ideas Backlog or generate new one
  ## For creative: ensure divergence from previous approaches

  # 3. ACT — make targeted changes (one hypothesis per waypoint)
  # Modify files, write code, adjust config...

  # 4. VERIFY — run the 4-layer verification pipeline
  ## Layer 0: Syntax check (fast, mandatory) — fail = immediate discard
  ## Layer 1: Guard checks (user-defined, mandatory) — fail = revert + discard
  ## Layer 2: Primary metric (user-defined) — collect numeric value
  ## Layer 3: Quality checks (optional) — collect secondary values

  # 5. DECIDE — keep or discard based on orientation strategy
  IF all guards pass AND metric improved (per orientation threshold):
    git add -A && git commit -m "waypoint-{N}: KEEP — {description}"
    Log to odyssey.jsonl: {run, commit, metric, status: "keep", description}
    Update MISSION.md: add to "Wins", update "Current Best"
    Reset consecutive_discards to 0
  ELSE:
    git reset --hard HEAD~1  # Roll back to checkpoint
    Log to odyssey.jsonl: {run, status: "discard", description, reason}
    Update MISSION.md: add to "Dead Ends"
    Increment consecutive_discards

  # 6. RECORD — update all state files
  ## Update MISSION.md frontmatter (total_waypoints, best_metric, consecutive_discards)
  ## Update .claude/odyssey.local.md (iteration, consecutive_discards)
  ## Commit state files

  # 7. RECAP — one-line progress marker, then CONTINUE
  # Pick next most impactful improvement from backlog
  # DO NOT stop, DO NOT ask for permission

  # 8. STOP CONDITIONS (only these stop the loop)
  ## Stop hook handles: max-iterations, time-budget, completion-promise
  ## Stuck detection: 10 consecutive discards → pause for direction
  ## User interrupt: /odyssey-cancel
```

## Orientation Strategies

### Engineer (default)
- **Compass**: Conservative. Prioritize changes that pass guards. Small atomic commits.
- **Threshold**: Strict. Must pass all guards AND not degrade metrics. Equal metric + simpler code = keep.
- **Best for**: CI/CD pipelines, auth modules, database migrations, infrastructure.

### Creative
- **Compass**: Divergent. Force diversity — if last 3 waypoints used similar approaches, propose something structurally different. Use odyssey-explorer agent for inspiration.
- **Threshold**: Lenient. Keep if any interesting signal, even if metrics degrade slightly. "Interesting" = new behavior, unexpected interaction, or surprise finding.
- **Extra mechanisms**: Exploration branches (`explore/{n}`), surprise detection, cross-pollination searches.
- **Best for**: Architecture exploration, performance breakthroughs, unconventional solutions.

### Production
- **Compass**: Progressive. Each waypoint must leave the system fully functional. No half-finished refactors.
- **Threshold**: Rigorous. Must pass guards AND improve primary metric AND introduce no new warnings.
- **Extra mechanisms**: Regression guard, change minimization (fewer lines wins ties), deployment readiness check.
- **Best for**: Performance optimization, bug fixes, deployment preparation.

### Combined
Specify multiple orientations: `[engineer, creative]` means use engineer by default, switch to creative if stuck for 5 waypoints.

See [compass-strategies.md](references/compass-strategies.md) for detailed strategies.

## Verification Pipeline

| Layer | Purpose | Timeout | Failure |
|-------|---------|---------|---------|
| 0 — Syntax | Catch parse errors | 10s | immediate discard |
| 1 — Guard | User-defined constraints | 120s | revert + discard |
| 2 — Metric | Optimization target | 600s | compare and decide |
| 3 — Quality | Secondary checks | 60s | warning only |

Auto-detection: Cargo.toml → Rust, package.json+tsconfig → TypeScript, go.mod → Go, pyproject.toml → Python.

See [verification-patterns.md](references/verification-patterns.md) for details.

## State Files

| File | Purpose | Managed by |
|------|---------|------------|
| `MISSION.md` | Task definition + living progress log | Agent (auto-updated) |
| `odyssey.jsonl` | Structured experiment log | odyssey_helper.py |
| `odyssey.ideas.md` | Hypothesis backlog | Agent + user |
| `.claude/odyssey.local.md` | Stop hook state | setup + stop-hook.sh |

## Commands

| Command | Purpose |
|---------|---------|
| `/odyssey "goal" [--orientation] [--max-iterations N]` | Start a new mission |
| `/odyssey --resume` | Resume existing mission |
| `/odyssey-status` | Show current progress |
| `/odyssey-cancel` | Stop active mission |

## Rules

1. **Never break the guard** — if any guard fails, rollback immediately
2. **One hypothesis per waypoint** — small, focused, easy to evaluate
3. **Record everything** — odyssey.jsonl is the experiment log, MISSION.md is the living document
4. **Don't repeat failures** — read "What's Been Tried" before each waypoint
5. **No asking for permission mid-loop** — autonomous until user interrupts
6. **Recap is a progress marker, not a stop** — note what was done, then continue
7. **Prioritize by impact** — functional integrity > metric improvement > polish

## The Goliath Pattern (Creative Mode)

When facing a "giant" — a task that seems impossible with standard approaches:

1. **Sling**: Gather 3-5 diverse approaches before committing (don't use Saul's armor = don't copy-paste standard solutions)
2. **Precision Strike**: Test the most unexpected approach first
3. **Surprise Detection**: If the result contradicts your hypothesis, flag it — that's where the real insight lives
4. **Record the Story**: Every giant encountered goes into "Surprises" in MISSION.md

## Final Report (produced only when loop stops)

```
ODYSSEY COMPLETE
================
Mission:      {title}
Branch:       odyssey/{name}
Orientation:  {orientation}
Waypoints:    {N} total | {X} kept | {Y} discarded
Result:       SUCCESS | PARTIAL | STUCK

Key changes:
1. ...
2. ...

odyssey.jsonl summary:
{helper summary output}
```

## Detailed References

- [loop-procedures.md](references/loop-procedures.md) — step-by-step execution
- [compass-strategies.md](references/compass-strategies.md) — orientation strategies
- [verification-patterns.md](references/verification-patterns.md) — verification pipeline
- [mission-format.md](references/mission-format.md) — MISSION.md specification
