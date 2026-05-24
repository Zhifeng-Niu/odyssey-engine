# Compass Strategies — Orientation Details

## Engineer Orientation

**Philosophy**: Reliability first. Every change must pass all existing guards. Small, atomic commits that are easy to review.

### Compass Behavior
1. **Hypothesis selection**: Pick from the Ideas Backlog, ordered by confidence
2. **Change scope**: Small, targeted changes. Prefer modifying one file over five.
3. **Risk tolerance**: Low. If unsure whether a change will pass guards, choose a safer approach.
4. **Stuck recovery**: If 5 consecutive discards, switch to second orientation or pause.

### Decision Matrix
| Guards | Metric | Complexity | Decision |
|--------|--------|------------|----------|
| Pass | Improved | Lower | KEEP |
| Pass | Improved | Higher | KEEP (but note) |
| Pass | Same | Lower | KEEP |
| Pass | Same | Higher | DISCARD |
| Pass | Worse | Any | DISCARD |
| Fail | Any | Any | DISCARD + revert |

## Creative Orientation

**Philosophy**: Diversity over optimization. The goal is to explore the solution space, not to find the best solution immediately.

### Compass Behavior
1. **Divergence tracking**: Track approach similarity across waypoints
   - Same type of change (parameter tuning vs structural) = low divergence
   - Same files modified = low divergence
   - Similar outcomes = low divergence
   - If 3 consecutive waypoints with similarity > 0.7: force structural change
2. **Hypothesis selection**: Rank approaches by novelty, not expected improvement
3. **Change scope**: Bold. Large structural changes are acceptable.
4. **Risk tolerance**: High. Failed experiments are valuable data.

### Exploration Patterns

**Sling (The Goliath Pattern)**:
Before committing to an approach, gather 3-5 diverse stones:
1. Launch odyssey-explorer agent to find approaches
2. Rank by novelty (not expected performance)
3. Pick the most unexpected one that's still plausible

**Cross-Pollination**:
Search other modules/projects for patterns that solve similar problems:
```
"Find patterns in this codebase that solve {problem} in a different module"
```

**Constraint Removal**:
Temporarily ignore one constraint and see what becomes possible:
- "What if we didn't need to maintain backward compatibility?"
- "What if we could use O(n²) memory?"
- "What if latency didn't matter?"

**Inversion**:
Instead of optimizing, try to make things worse:
- "What makes this slow?" → The answer often reveals the fix

**Random Walk** (1 in 5 waypoints):
Make a change with no expected improvement. Observe the system's response.

### Surprise Detection
A waypoint is a "surprise" when:
- The metric moved in the opposite direction from the hypothesis
- A change in module A affected module B unexpectedly
- A "safe" change broke something, or a "risky" change worked perfectly

Surprises are logged with extra detail in MISSION.md "Surprises" section.

### Decision Matrix
| Result | Novel | Decision |
|--------|-------|----------|
| Improved | Yes | KEEP — best case |
| Improved | No | KEEP — but consider it well-explored |
| Degraded | Yes | KEEP — the surprise is valuable |
| Degraded | No | DISCARD — pure noise |
| No change | Yes | KEEP — learn from the non-result |
| No change | No | DISCARD — nothing learned |

## Production Orientation

**Philosophy**: Ship-ready at every step. No half-finished refactors. Each waypoint must leave the system in a fully deployable state.

### Compass Behavior
1. **Hypothesis selection**: Pick the smallest change likely to improve the metric
2. **Change scope**: Minimal. The fewer lines changed, the better.
3. **Risk tolerance**: Very low. Every change is treated as if it will be deployed immediately.
4. **Freeze mechanism**: If no metric improvement for 5 consecutive waypoints, switch to "polish" phase (code quality, documentation, edge cases).

### Additional Mechanisms

**Regression Guard**: After each keep, run comprehensive tests (not just primary guard):
```bash
{full_test_suite_command}
```

**Change Minimization**: When two approaches produce equal metric improvement:
- Count lines changed (`git diff --stat HEAD~1`)
- The one with fewer lines wins
- If equal, prefer the one that's easier to understand

**Deployment Readiness Check**: Final validation before considering the mission complete:
- No hardcoded values
- No TODO/FIXME comments in changed files
- No missing error handling
- No untested edge cases
- Documentation updated

### Decision Matrix
| Guards | Metric | New Issues | Lines Changed | Decision |
|--------|--------|------------|---------------|----------|
| Pass | Improved | None | Any | KEEP |
| Pass | Improved | Warnings | Any | DISCARD (fix warnings first) |
| Pass | Same | None | < 20 | KEEP (simplification) |
| Pass | Same | None | > 20 | DISCARD (no value) |
| Pass | Worse | None | Any | DISCARD |
| Fail | Any | Any | Any | DISCARD + revert |

## Combined Orientations

Specify multiple in MISSION.md: `orientation: [engineer, creative]`

- Primary orientation is the default strategy
- If stuck (5 consecutive discards), switch to secondary
- If secondary also stuck, pause for user direction
- Compass logs which orientation was active for each waypoint

## Stuck Detection and Recovery

**Stuck = 10 consecutive discards**

The stop hook will inject a warning. The agent should:

1. Analyze the pattern of failures — are they all the same type?
2. Consider switching orientation
3. Consider broadening scope (maybe the constraint is wrong)
4. Consider narrowing scope (maybe the task is too large)
5. Output `<promise>STUCK</promise>` to exit gracefully if no path forward
