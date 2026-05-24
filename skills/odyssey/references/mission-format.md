# Mission Format — MISSION.md Specification

## Overview

MISSION.md is the primary interface between the human and the Odyssey Engine. It is both a specification (written by the human) and a living document (auto-updated by the engine).

## Sections

### Frontmatter (YAML)

```yaml
---
orientation: [engineer]           # Required. engineer | creative | production. Can combine.
status: active                     # Auto-managed: active | paused | completed | abandoned
started_at: 2026-05-24            # Auto-filled on start
expedition_branch: null            # Auto-filled on branch creation
baseline_metric: null              # Auto-filled after baseline run
best_metric: null                  # Auto-updated on each keep
total_waypoints: 0                 # Auto-updated
consecutive_discards: 0            # Auto-updated
---
```

### Goal (Required, Human-Edited)

One sentence. The compass bearing. Everything the engine does should move toward this goal.

```markdown
## Goal
Reduce p99 API response time below 200ms while maintaining 100% test coverage.
```

### Context (Optional, Human-Edited)

Why this matters. What's the current state. Any background the agent needs.

```markdown
## Context
The API currently has p99 latency of 450ms. The database connection pool is
configured with 10 connections. Recent profiling shows 70% of time is spent
in database queries.
```

### Scope (Required, Human-Edited)

Define what can and cannot be modified.

```markdown
## Scope

### Modifiable
- `src/api/**/*.py` — API endpoint handlers
- `src/db/connection.py` — Database connection management
- `config/pool.yaml` — Connection pool configuration

### Read-Only (PROTECTED — never modify)
- `src/api/public/**` — Public API contracts must not change
- `migrations/**` — No schema changes
- `tests/**` — Existing tests must not be removed
```

### Metrics (Required, Human-Edited)

Define measurable criteria.

```markdown
## Metrics

| Name | Unit | Measure Command | Direction |
|------|------|----------------|-----------|
| p99_ms | ms | `bash odyssey.sh` | lower |
| coverage | % | `pytest --cov \| grep TOTAL \| awk '{print $4}'` | higher |
```

### Guard (Required, Human-Edited)

A command that must exit 0 for any change to be kept.

```markdown
## Guard
\`\`\`bash
pytest --tb=short -q
\`\`\`
```

### Termination (Required, Human-Edited)

When to stop the loop.

```markdown
## Termination
- p99_ms < 200 AND all tests pass
- OR max 50 waypoints
- OR user interrupt
```

### What's Been Tried (Auto-Managed)

The engine updates this section. **Do not edit manually.**

```markdown
## What's Been Tried

### Wins
- Run #1: Added connection pooling → p99 450→320ms (keep)
- Run #5: Added prepared statement cache → p99 320→245ms (keep)

### Dead Ends
- Run #2: Async connection pool → deadlock in tests (discard)
- Run #4: Response compression → p99 unchanged, added CPU overhead (discard)

### Surprises
- Run #7: Expected query caching to help, but p99 increased by 15%. Investigation
  revealed cache serialization cost exceeded query cost. Bottleneck is not DB queries
  but response serialization.
```

### Current Best (Auto-Managed)

```markdown
## Current Best
- p99_ms: 245ms (Run #5)
- Baseline: 450ms
- Improvement: -45.6%
```

### Ideas Backlog (Human + Auto)

```markdown
## Ideas Backlog

### High Priority
- [ ] Try HTTP/2 multiplexing for batch requests
- [ ] Add query result caching with 60s TTL

### Tried and Abandoned
- [x] Async pool → deadlock (Run #2)
- [x] Response compression → no improvement (Run #4)
```

## What's Auto-Managed vs. Human-Edited

| Section | Who Manages | Notes |
|---------|-------------|-------|
| Frontmatter | Engine | All fields auto-updated |
| Goal | Human | The mission target |
| Context | Human | Background info |
| Scope | Human | What can/cannot change |
| Metrics | Human | What to measure |
| Guard | Human | What must pass |
| Termination | Human | When to stop |
| What's Been Tried | Engine | Never edit manually |
| Current Best | Engine | Never edit manually |
| Ideas Backlog | Both | Human can add, engine marks tried |

## Example Missions

### Engineer: Build Auth Module
```yaml
orientation: [engineer]
```
```markdown
## Goal
Implement JWT authentication with session management for the API.

## Guard
cargo test --lib auth

## Metrics
| Name | Unit | Measure Command | Direction |
|------|------|----------------|-----------|
| coverage | % | `cargo tarpaulin --out Stdout | grep TOTAL | awk '{print $4}'` | higher |

## Termination
- coverage > 90% AND all auth tests pass
- OR max 30 waypoints
```

### Creative: Architecture Exploration
```yaml
orientation: [creative, engineer]
```
```markdown
## Goal
Find an unconventional approach to reduce event processing latency by 50%.

## Guard
npm test

## Metrics
| Name | Unit | Measure Command | Direction |
|------|------|----------------|-----------|
| p50_ms | ms | `node benchmark.js | grep p50 | awk '{print $2}'` | lower |

## Termination
- p50_ms < 25ms
- OR max 40 waypoints
- OR user interrupt
```

### Production: Performance Optimization
```yaml
orientation: [production]
```
```markdown
## Goal
Reduce Docker image size below 100MB while maintaining all functionality.

## Guard
npm test && npm run build

## Metrics
| Name | Unit | Measure Command | Direction |
|------|------|----------------|-----------|
| image_mb | MB | `docker images app:latest --format "{{.Size}}" | sed 's/MB//'` | lower |

## Termination
- image_mb < 100 AND all tests pass AND build succeeds
- OR max 20 waypoints
```
