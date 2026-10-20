---
orientation: [engineer]
status: active
started_at: 2026-10-20T16:37:17Z
expedition_branch: odyssey/20261021-003717
baseline_metric: null
best_metric: null
total_waypoints: 0
consecutive_discards: 0
---

# Mission: Absorb autodev's genuine strengths so odyssey strictly dominates it: composite w

## Goal
Absorb autodev's genuine strengths so odyssey strictly dominates it: composite weighted quality gates (L1 build+tests, L2 structured review rubric, L3 security+perf, L4 regression), simplicity criterion, crash/churn protocol — implemented odyssey-native in the convergence layer, with a real test suite

## Context
Project type: generic. Auto-detected guard: none.

## Scope

### Modifiable
- (auto — all files not in Read-Only)

### Read-Only (PROTECTED)
- (none specified)

## Arsenal

Capabilities engaged for this mission (skills / agents / LSPs / MCP tools).
Living section — extend as the mission discovers new needs.

| Capability | Use when |
|------------|----------|
| (populate at mission start) | |

## Metrics

| Name | Unit | Measure Command | Direction |
|------|------|----------------|-----------|
| manual | - | (auto-detected) | lower |

## Guard
```bash
echo "no guard defined"
```

## Termination
- Task complete (all checks pass AND metric improved)
- OR stuck (10 consecutive discards)
- OR user interrupt (/odyssey-cancel)
- No iteration limit — runs until done

## What's Been Tried

### Wins
- wp1: 13-test suite (convergence/pivot/drift/hook-contract) — failing=0. Regression net for all later waypoints.
- wp2: `score` cmd — weighted L1-L4, simplicity criterion, hard-fail. Composite 9.5 (parity cap: no test bonus yet).

### Dead Ends
{Auto-updated by engine.}

### Surprises
- wp3: own churn test caught its own ordering bug (churn check was unreachable behind the insufficient-data early return) — the loop's tests are the sharper reviewer.
- Simplicity criterion cannot see capability expansion once L1/L4 sit at cap 10: equal composite + more lines reads as "discard" for pure feature work. Resolution: mission Goal is the compass for feature keeps; gates guard regressions. Candidate: capability dimension in score.

## Current Best
- metric: failing=0 (tests)
- Baseline: (pending)

## Ideas Backlog
- verification-patterns.md: structured L2 review rubric (5 dims x 0-2) wired to score --l2
- README: feature matrix odyssey vs autodev (dominance table)
- capability dimension in score (fix the cap blindness recorded in Surprises)
