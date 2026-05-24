# Odyssey Engine

Universal autonomous iteration engine. For any task that benefits from structured experimentation — code, research, writing, design, data analysis, and beyond.

**Fuses**: autoresearch (metric-driven experiments) + gaggle-iterate (checkpoint/verify/rollback) + ralph-loop (continuous execution).

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
# Claude Code — via plugin marketplace
/plugin install Zhifeng-Niu/odyssey-engine

# Or clone and link
git clone https://github.com/Zhifeng-Niu/odyssey-engine.git ~/.claude/plugins/odyssey-engine
```

## Quick Start

```
# Code optimization
/odyssey "Reduce API latency below 200ms" --orientation production --max-iterations 20

# Research exploration
/odyssey "Find the most promising architecture for event processing" --orientation creative

# Writing refinement
/odyssey "Improve this essay's readability score to grade 8 level" --orientation engineer

# Resume
/odyssey --resume
```

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
- OR max 50 waypoints
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
├── plugin.json              # Plugin manifest
├── skills/odyssey/
│   ├── SKILL.md             # Core loop definition
│   └── references/          # Detailed strategies
├── commands/                # /odyssey, /odyssey-status, /odyssey-cancel
├── agents/                  # odyssey-explorer, odyssey-critic
├── hooks/
│   └── stop-hook.sh         # Continuous execution engine
├── scripts/
│   ├── setup-odyssey.sh     # Mission initialization
│   └── odyssey_helper.py    # JSONL management + project detection
└── templates/
    └── MISSION.md.template
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
- `--max-iterations` hard cap
- `--time-budget` optional limit
- 10 consecutive discards → pause for direction
- Protected files (read-only scope) auto-reverted if modified

## Commands

| Command | Purpose |
|---------|---------|
| `/odyssey "goal" [options]` | Start a new mission |
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

## License

MIT
