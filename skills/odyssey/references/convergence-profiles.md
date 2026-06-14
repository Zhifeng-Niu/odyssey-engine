# Convergence Profiles — Adaptive Convergence Reference

The Odyssey Engine adapts its convergence behavior to project characteristics. Instead of hardcoded "10 discards / 3 diminishing returns", each mission gets a ConvergenceProfile based on delivery tier.

## Profile Parameters

| Parameter | Purpose | Default (standard) |
|-----------|---------|-------------------|
| `patience_budget` | Hard cap on total waypoints | 30 |
| `discard_threshold` | Consecutive discards triggering stuck | 10 |
| `min_metric_delta_pct` | Avg delta below this = diminishing | 0.5% |
| `convergence_window` | Keeps examined for convergence | 5 |
| `guard_timeout_mult` | Multiplier on Layer 1 timeout | 1.0x |
| `auto_orient_switch` | Auto-rotate orientation when stuck | true |

## Tier Reference

### prototype
```yaml
patience_budget: 15
discard_threshold: 5
min_metric_delta_pct: 1.0
convergence_window: 3
guard_timeout_mult: 0.5
auto_orient_switch: true
```

**When**: throwaway scripts, demos, experiments, no tests/CI.
**Why so impatient**: prototype code is disposable. If 5 attempts fail, the approach is wrong — switch tactic.
**Example**: `/odyssey "scrape this URL and parse JSON" --tier prototype`

### standard
```yaml
patience_budget: 30
discard_threshold: 10
min_metric_delta_pct: 0.5
convergence_window: 5
guard_timeout_mult: 1.0
auto_orient_switch: true
```

**When**: typical project with tests or CI but not deployed at scale.
**Why balanced**: 30 attempts is enough to explore 5-6 distinct hypotheses with retries.
**Example**: most internal tools, libraries in development.

### production
```yaml
patience_budget: 50
discard_threshold: 15
min_metric_delta_pct: 0.1
convergence_window: 5
guard_timeout_mult: 2.0
auto_orient_switch: false  # critical: human review required
```

**When**: mission-critical code, semver ≥ 1.0, has tests + CI + changelog.
**Why patient + strict**: small improvements (0.1%) compound at scale. No auto-switch because changing strategy mid-mission on production code is risky — human should decide.
**Example**: `/odyssey "Reduce p99 API latency" --orientation production --tier production`

### research
```yaml
patience_budget: 100
discard_threshold: 20
min_metric_delta_pct: 0.0  # any movement counts
convergence_window: 10
guard_timeout_mult: 1.0
auto_orient_switch: true
```

**When**: open-ended exploration, hypothesis testing, no guard.
**Why so patient**: in research, "no improvement" is still data. Discarding 20 attempts means you've learned 20 things don't work — that's progress.
**Example**: `/odyssey "Find unconventional architectures for event processing" --orientation creative --tier research`

## Auto-Inference Logic

`odyssey_helper.py detect` infers tier from project signals:

```
production  ← has_tests AND has_ci AND version_major>=1 AND (has_changelog OR has_docs)
research    ← (no guard) AND (no tests) AND has_docs
standard    ← has_tests OR has_ci OR has_changelog
prototype   ← (none of the above)
```

### Signal Detection

| Signal | How Detected |
|--------|-------------|
| `has_tests` | `tests/` dir, `test_*.py`, `*_test.go`, `*.test.ts`, `__tests__/`, etc. |
| `has_ci` | `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/`, etc. |
| `has_changelog` | `CHANGELOG.md`, `CHANGES.md`, `HISTORY.md` |
| `has_docs` | `docs/` dir, `doc/` dir, or `README.md` |
| `version_major` | First integer from `version` in package.json / plugin.json / Cargo.toml / pyproject.toml |
| `code_size` | S/M/L/XL based on source file count |

## Manual Override

### Via CLI Flag
```bash
/odyssey "mission" --tier production
```

### Via MISSION.md Frontmatter
```yaml
---
delivery_tier: production
---
```

### Via Direct Edit of State File
```bash
sed -i '' 's/^delivery_tier:.*/delivery_tier: production/' .claude/odyssey.local.md
sed -i '' 's/^patience_budget:.*/patience_budget: 50/' .claude/odyssey.local.md
```

## Convergence Detection Algorithm

`odyssey_helper.py convergence-check --jsonl PATH --tier T` runs this:

```python
window = profile.convergence_window  # e.g. 5
min_delta = profile.min_metric_delta_pct  # e.g. 0.5

recent_keeps = keeps[-window:]
metrics = [e.metric for e in recent_keeps]

# Compute avg relative delta
deltas = []
for i in range(1, len(metrics)):
    rel = abs(metrics[i] - metrics[i-1]) / abs(metrics[i-1]) * 100
    deltas.append(rel)
avg_delta = mean(deltas)

# Three checks
converged = (
    avg_delta < min_delta  # diminishing returns
    OR total_waypoints >= patience_budget  # exhausted budget
)
# Note: stuck (consecutive discards) is NOT convergence;
# it triggers orientation switch in stop-hook.sh
```

Output:
```json
{
  "converged": true,
  "reason": "diminishing returns: avg delta 0.300% < threshold 1.0% over last 3 keeps",
  "evidence": [...],
  "tier": "prototype",
  "window": 3
}
```

## Integration with Stop Hook

`hooks/stop-hook.sh` runs convergence-check before each waypoint:

```bash
conv_result=$(python3 odyssey_helper.py convergence-check \
  --jsonl odyssey.jsonl --tier "$delivery_tier")

if [[ "$converged" == "true" ]]; then
  deactivate "converged: $reason"  # allow exit
fi
```

This means the agent does NOT need to output `<converged/>` — the hook decides based on data. The agent can still force-exit via `<converged/>` if it judges the data is misleading.

## Debugging Profiles

### Print current profile
```bash
python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py profile --tier standard
python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py profile --path .  # auto-infer
```

### Run convergence-check manually
```bash
python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py convergence-check \
  --jsonl odyssey.jsonl --tier standard
```

### See what tier would be inferred for a project
```bash
python3 $CLAUDE_PLUGIN_ROOT/scripts/odyssey_helper.py detect --path /some/project
```

## When to Pick a Non-Default Tier

| Situation | Recommended Tier |
|-----------|-----------------|
| Hackathon project | prototype |
| Internal tool with tests | standard |
| Customer-facing API | production |
| Architecture spike | research |
| Bug fix on legacy code | standard |
| Performance optimization on deployed service | production |
| Documentation improvement | research |
| Demo for conference talk | prototype |
