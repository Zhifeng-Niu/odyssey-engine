# Odyssey Engine

Autonomous iteration engine for Claude Code. Three orientations, one loop.

**Fuses**: autoresearch (metric-driven experiments) + gaggle-iterate (checkpoint/verify/rollback) + ralph-loop (continuous execution).

## What It Does

Odyssey Engine runs autonomous iteration loops that adapt strategy to the task:

| Orientation | Best For | Strategy |
|-------------|----------|----------|
| **engineer** | CI/CD, auth modules, infrastructure | Conservative, atomic commits, guard-first |
| **creative** | Architecture exploration, breakthroughs | Divergent, force diversity, surprise detection |
| **production** | Performance optimization, deployment prep | Progressive, minimal changes, ship-ready every step |

## Install

```bash
# Claude Code — via plugin marketplace
/plugin install Zhifeng-Niu/odyssey-engine

# Or clone and link
git clone https://github.com/Zhifeng-Niu/odyssey-engine.git ~/.claude/plugins/odyssey-engine
```

## Quick Start

```
/odyssey "Reduce API latency below 200ms" --orientation production --max-iterations 20
/odyssey "Find unconventional layout approaches" --orientation creative --max-iterations 10
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

## Origin

Built from three systems:
- **autoresearch** (karpathy) — metric-driven experimentation, JSONL tracking
- **gaggle-iterate** — checkpoint/verify/rollback loop
- **ralph-loop** — stop-hook-based continuous execution

Named for the Odyssey — every mission is a journey with giants to face, each requiring a different strategy.

## License

MIT
