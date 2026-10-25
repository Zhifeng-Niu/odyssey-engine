# Odyssey Engine

Universal autonomous iteration engine. For any task that benefits from structured experimentation — code, research, writing, design, data analysis, and beyond.

**Fuses**: autoresearch (metric-driven experiments) + gaggle-iterate (checkpoint/verify/rollback) + ralph-loop (continuous execution).

> **The amplifier theorem**: the same model performs differently under
> different harnesses. Odyssey's mission is to raise the capability floor —
> a non-flagship model under this harness should outperform a flagship
> model under none. Persistence, honest self-assessment, and procedure are
> **externalized** (stop hook, data-driven convergence, waypoint
> scaffolding) so agent value becomes a property of the *system*, not the
> model alone. See [docs/model-adaptive-harness.md](docs/model-adaptive-harness.md).

## What It Does

Odyssey Engine runs autonomous iteration loops that adapt strategy to the task at hand — not just code, but anything you can measure and iterate on:

| Orientation | Best For | Strategy |
|-------------|----------|----------|
| **engineer** | Systems, infrastructure, pipelines, scaffolding | Conservative, atomic steps, guard-first |
| **creative** | Research, exploration, breakthroughs, design | Divergent, force diversity, surprise detection |
| **production** | Optimization, hardening, deployment preparation | Progressive, minimal changes, ship-ready every step |

### Not Just Code

Odyssey handles any iterative task:
- **Research**: iterate on hypotheses, track evidence, converge on insight
- **Writing**: draft → critique → refine, measure clarity or engagement
- **Design**: explore variations, A/B compare, evolve toward a target
- **Data analysis**: try models, compare accuracy, log what worked
- **Code**: build, test, optimize, harden — the full engineering cycle

## Install

```bash
# Add the repo as a marketplace, then install (CLI)
claude plugin marketplace add Zhifeng-Niu/odyssey-engine
claude plugin install odyssey-engine@odyssey-engine

# Or inside a Claude Code session
/plugin marketplace add Zhifeng-Niu/odyssey-engine
/plugin install odyssey-engine@odyssey-engine
```

## Quick Start

```
# Code optimization — auto-infers tier from project, runs until data-driven convergence
/odyssey "Reduce API latency below 200ms" --orientation production

# Explicit tier override
/odyssey "Mission-critical optimization" --orientation production --tier production

# Research exploration (100 waypoint patience, any delta counts)
/odyssey "Find the most promising architecture for event processing" --orientation creative --tier research

# Throwaway script (15 waypoint patience, fast give-up)
/odyssey "Scrape this URL and parse JSON" --tier prototype

# With time budget (optional)
/odyssey "Refactor the auth module" --orientation production --time-budget 30m

# Resume
/odyssey --resume
```

## Adaptive Convergence

The loop adapts its patience and convergence thresholds based on project type:

| Tier | Patience | Discard Limit | Min Delta | Auto-Switch | Inferred When |
|------|----------|---------------|-----------|-------------|---------------|
| **prototype** | 15 | 5 | 1.0% | yes | No tests, no CI, no changelog |
| **standard** | 30 | 10 | 0.5% | yes | Has tests OR CI OR changelog |
| **production** | 50 | 15 | 0.1% | **no** | tests + CI + version≥1.0 + docs/changelog |
| **research** | 100 | 20 | any | yes | No guard, exploratory |

Auto-inference signals: `tests/`, `test_*.py`, `.github/workflows/`, `CHANGELOG.md`, `version` in package.json/plugin.json/Cargo.toml, `docs/`.

Override with `--tier`. See [convergence-profiles.md](skills/odyssey/references/convergence-profiles.md) for details.

## How It Works

### The Loop

```
WAYPOINT += 1

1. CHECKPOINT  — git commit current state
2. COMPASS     — choose next approach based on orientation
3. ACT         — make one focused change
4. VERIFY      — run 4-layer verification pipeline
5. DECIDE      — keep (commit) or discard (git reset --hard)
6. RECORD      — log to odyssey.jsonl, update MISSION.md
7. CONTINUE    — stop hook prevents exit, loop continues
```

### Convergence

Odyssey runs until the task is done — no fixed iteration limit. **Convergence is detected by objective data**, not agent self-report:

- **Data-driven convergence**: stop hook runs `odyssey_helper.py convergence-check` before each waypoint. Auto-deactivates when avg metric delta over last N keeps < tier's min_delta_pct, OR patience budget exhausted.
- **Adaptive profiles**: four delivery tiers (prototype/standard/production/research) with distinct patience/discard/delta parameters, auto-inferred from project signals (tests, CI, changelog, version, docs).
- **Auto orientation switch**: when stuck, non-production tiers auto-rotate orientation (engineer→creative→production). Production tier requires human review.
- **User interrupt**: `/odyssey-cancel` at any time
- **Time budget**: optional `--time-budget` hard cap

The agent can still force-exit via `<converged/>` if it judges the data misleading, but normally the data decides.

### MISSION.md

Tasks are defined in a living document that the engine reads and updates:

```markdown
# Mission: Optimize API Latency

## Goal
Reduce p99 response time below 200ms.

## Guard
pytest --tb=short -q

## Metrics
| Name | Measure | Direction |
|------|---------|-----------|
| p99_ms | `bash odyssey.sh` | lower |

## Termination
- p99_ms < 200 AND all tests pass
- OR convergence detected
- OR user interrupt
```

### Verification Pipeline

| Layer | Purpose | Failure |
|-------|---------|---------|
| 0 — Syntax | Catch parse errors | immediate discard |
| 1 — Guard | User-defined constraints | revert + discard |
| 2 — Metric | Optimization target | compare and decide |
| 3 — Quality | Secondary checks | warning only |

### Project Auto-Detection

Detects project type and configures verification automatically:

| Sentinel | Type | Syntax Check | Guard |
|----------|------|-------------|-------|
| `Cargo.toml` | Rust | `cargo check` | `cargo test` |
| `package.json` + `tsconfig.json` | TypeScript | `tsc --noEmit` | `npm test` |
| `go.mod` | Go | `go vet` | `go test` |
| `pyproject.toml` | Python | `ast.parse` | `pytest` |

## The Goliath Pattern

When facing a "giant" — a task that seems impossible:

1. **Sling**: Gather 3-5 diverse approaches before committing (don't use borrowed armor)
2. **Precision Strike**: Test the most unexpected approach first
3. **Surprise Detection**: If the result contradicts your hypothesis, that's where the real insight lives
4. **Record the Story**: Every giant goes into "Surprises" in MISSION.md

## Architecture

```
odyssey-engine/
├── .claude-plugin/          # Plugin spec: plugin.json + marketplace.json
├── docs/                    # Dev log (iterations.tsv), specs
├── skills/odyssey/
│   ├── SKILL.md             # Core loop definition
│   └── references/          # Detailed strategies (5 files)
│       ├── loop-procedures.md
│       ├── compass-strategies.md
│       ├── verification-patterns.md
│       ├── mission-format.md
│       └── convergence-profiles.md
├── commands/                # /odyssey, /odyssey-status, /odyssey-cancel
├── agents/                  # odyssey-explorer, odyssey-critic
├── hooks/
│   └── stop-hook.sh         # Continuous execution + adaptive convergence detection
├── scripts/
│   ├── setup-odyssey.sh     # Mission initialization + tier inference
│   ├── odyssey_helper.py    # JSONL mgmt + project detect + convergence check
│   └── sync-cache.sh        # CC plugin cache sync
└── templates/
    └── MISSION.md.template  # Single source of truth for MISSION.md
```

## State Files

| File | Purpose |
|------|---------|
| `MISSION.md` | Task definition + living progress log |
| `odyssey.jsonl` | Structured experiment log |
| `odyssey.ideas.md` | Hypothesis backlog |
| `.claude/odyssey.local.md` | Stop hook state |

## Safety

- Git checkpoint before every change — `git reset --hard` on failure
- Stop hook prevents premature exit
- Convergence detection — agent self-stops when improvements plateau
- `--time-budget` optional hard limit
- 10 consecutive discards → pause for direction
- `<converged/>` signal for clean exit
- Protected files (read-only scope) auto-reverted if modified

## Commands

| Command | Purpose |
|---------|---------|
| `/odyssey "goal" [options]` | Start a new mission (runs until converged) |
| `/odyssey --resume` | Resume existing mission |
| `/odyssey-status` | Show progress |
| `/odyssey-cancel` | Stop mission |

## Why Odyssey Exists

Odyssey was born from a specific frustration: two tools that each did half the job.

**gaggle-iterate** (a personal adaptation of [autoresearch](https://github.com/karpathy/autoresearch) by [Andrej Karpathy](https://github.com/karpathy)) had excellent per-iteration recap and decision-making — checkpoint → experiment → verify → keep/discard. The recap mechanism meant each iteration genuinely learned from the last. But it couldn't loop. Every run was manual. No continuity.

**[ralph-loop](https://claude.com/plugins/ralph-loop)** could run forever — the stop hook made continuous execution reliable and effortless. But each iteration replayed the same static prompt. The loop never evolved. No recap, no learning, no experiment tracking.

**Odyssey** fuses both: the evolving intelligence of gaggle-iterate's recap-driven iteration with ralph-loop's unstoppable execution engine. Each waypoint learns from the last. The mission state is a living document, not a replayed prompt. The loop runs until the job is done.

From **autoresearch** specifically: metric-driven evaluation, JSONL experiment tracking, `program.md`-style task definition, and git-based checkpoint/rollback — the DNA of the scientific method applied to autonomous agents.

---

> The Odyssey is the story — a long journey home, encountering giants at every turn, each demanding a different strategy.
> Goliath is embedded within it: a reminder that the smallest stone, thrown with precision at the right moment, can bring down what seemed invincible.

## vs autodev (feature dominance)

odyssey absorbed the genuinely good parts of the autodev pattern — and
kept its own advantages:

| Capability | autodev | odyssey |
|------------|---------|---------|
| Weighted composite quality gates (L1-L4) | ✅ hardcoded | ✅ `score` cmd, weights overridable per mission |
| Structured L2 review rubric | ✅ | ✅ verification-patterns + `--l2` |
| Regression layer + test-count incentives | ✅ | ✅ `--tests-added` / `--tests-removed` |
| Simplicity criterion (equal + fewer lines = win) | ✅ | ✅ encoded in `score` verdicts |
| Crash protocol, churn stop (5 consecutive) | ✅ | ✅ `--status crash`, `stale`/`churn` verdicts |
| Task definition | static `program.md` replayed | **living MISSION.md** — goal can pivot mid-flight (evidence re-partitioned) |
| Stopping criterion | fixed counts + plateau heuristics | **data-driven convergence** (diminishing returns / patience / churn / environment drift) |
| Human-judgment objectives | — | ✅ `--field content` persona jury + Goodhart guard |
| Adaptive (game-theoretic) environments | — | ✅ `--field strategy`: Board, anticipation ladder L0-L2, anti-leak keep gate, drift probes |
| Session capability surface | — | ✅ Arsenal: missions command all skills/agents/LSPs/MCP |
| Orientation & tier adaptation | — | ✅ 3 orientations × 4 tiers, auto-inferred |

## License

MIT
