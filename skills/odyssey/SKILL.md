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
/odyssey "Reduce API latency below 200ms" --orientation production
/odyssey "Find unconventional layout approaches" --orientation creative
/odyssey --resume
```

No --max-iterations. The loop runs until convergence (auto-detected) or user interrupt (/odyssey-cancel).

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
  ## Convergence: engine auto-detects via odyssey_helper.py convergence-check
  ##   - avg metric delta over last N keeps < tier's min_metric_delta_pct
  ##   - OR total waypoints >= tier's patience_budget
  ##   - (N = convergence_window: prototype=3, standard=5, production=5, research=10)
  ## Stuck: consecutive_discards >= tier's discard_threshold
  ##   - prototype/standard/research: auto-rotate orientation, reset discards, continue
  ##   - production: pause for human review
  ## User interrupt: /odyssey-cancel
  ## NO iteration limit — runs until converged, stuck (production only), or interrupted
```

## Arsenal — Full Capability Activation

A mission runs inside a full Claude Code session: **every installed skill,
plugin, agent, MCP server, and LSP is available to it.** Odyssey's own
components are the engine, not the toolbox — treat the whole session as
the mission's arsenal.

**At mission start (before waypoint 1):**
1. Inventory the capability surface relevant to THIS mission: skills
   (framework patterns, TDD, research, domain knowledge), agents
   (code-reviewer, security-reviewer, explorer…), LSP servers, MCP tools.
2. Select what serves the mission and record it in MISSION.md `## Arsenal`
   — one line each: capability → when to use. This section is living:
   extend it as the mission discovers new needs.

**During waypoints:**
- *Verification*: LSP diagnostics feed Layers 0/3; in production tier, run
  reviewer agents (code-reviewer, security-reviewer) on a diff before KEEP
- *Research (creative orientation)*: web search, docs skills, odyssey-explorer
  for cross-pollination
- *Domain knowledge*: reach for pattern skills before touching unfamiliar
  territory instead of improvising

**When stuck (compass move):**
An unused tool, skill, or agent is a legitimate hypothesis — often the
cheapest one on the board. Before rotating orientation, ask: *is there a
capability I haven't reached for?*

MCP tools follow the session's permission settings; if a tool would prompt
mid-loop, prefer alternatives that keep the mission autonomous.

## Convergence Profiles (Adaptive Convergence)

The loop self-terminates based on **objective data**, not agent self-assessment. Each mission gets a ConvergenceProfile based on project type and delivery tier.

### Four Delivery Tiers

| Tier | Patience | Discard Limit | Min Delta | Window | Auto-Switch | When |
|------|----------|---------------|-----------|--------|-------------|------|
| **prototype** | 15 | 5 | 1.0% | 3 | yes | Throwaway scripts, demos, no tests/CI |
| **standard** | 30 | 10 | 0.5% | 5 | yes | Typical project with tests or CI |
| **production** | 50 | 15 | 0.1% | 5 | **no** | Mission-critical, semver ≥ 1.0, tests+CI+changelog |
| **research** | 100 | 20 | 0.0% | 10 | yes | Open-ended exploration, no guard |

### Auto-Inference

Tier is auto-inferred from project signals:
- `tests/` dir, `test_*.py`, `*_test.go`, `*.spec.ts` → has_tests
- `.github/workflows`, `.gitlab-ci.yml`, `Jenkinsfile` → has_ci
- `CHANGELOG.md`, `CHANGES.md` → has_changelog
- `docs/`, `README.md` → has_docs
- `version` in package.json/plugin.json/Cargo.toml → version_major

Override with `--tier`:
```
/odyssey "mission" --orientation production --tier production
```

### How Convergence Is Detected

The stop hook runs `odyssey_helper.py convergence-check` before each waypoint. It returns `converged: true` when:

1. **Diminishing returns**: avg metric delta over last N keeps < tier's min_delta_pct
2. **Patience budget exhausted**: total waypoints >= tier's patience_budget
3. (Stuck is NOT convergence — it triggers orientation switch instead)

When converged, hook auto-deactivates and allows exit. Agent does NOT need to output `<converged/>` — the data decides.

### Stuck Recovery (Profile-Driven)

When `consecutive_discards >= discard_threshold`:
- If `auto_orient_switch: true` (prototype/standard/research): hook auto-rotates orientation (engineer→creative→production→engineer) and resets discards
- If `auto_orient_switch: false` (production): hook pauses for human review

See [convergence-profiles.md](references/convergence-profiles.md) for full parameter reference.

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

## Re-Entry Procedure (after Stop Hook)

When the stop hook fires and CC continues, follow this exact sequence:

1. Read `.claude/odyssey.local.md` to get current waypoint number and orientation
2. Read `MISSION.md` — scan "What's Been Tried" to avoid repeating failures
3. Pick ONE hypothesis from Ideas Backlog (or generate a new one based on orientation)
4. **Checkpoint**: `git add -A && git commit -m "waypoint-{N}: checkpoint"`
5. **Act**: Implement the single focused change
6. **Verify**: Run syntax check → guard command → collect metric
7. **Decide**:
   - KEEP: commit, log to `odyssey.jsonl`, update MISSION.md Wins, reset consecutive_discards
   - DISCARD: `git reset --hard HEAD~1`, log to `odyssey.jsonl`, update MISSION.md Dead Ends, increment consecutive_discards
8. **Record**: Update state files, commit
9. **One-line recap**, then immediately continue (stop hook handles the loop)

Do NOT stop. Do NOT ask for permission. The stop hook will re-fire after each waypoint.

## Commands

| Command | Purpose |
|---------|---------|
| `/odyssey "goal" [--orientation] [--time-budget 30m]` | Start a new mission (runs until convergence detected or /odyssey-cancel) |
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
- [convergence-profiles.md](references/convergence-profiles.md) — adaptive convergence tiers
