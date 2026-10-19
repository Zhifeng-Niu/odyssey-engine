# Official Marketplace Submission Package

> One manual step remains: the plugin directory submission form
> (linked from anthropics/claude-plugins-official → Contributing → External Plugins).
> Everything below is ready to paste. Requires: working install from a public
> repo (verified: `marketplace add` + `install` both succeed against this repo),
> `.claude-plugin/plugin.json` (present), standard structure (present).

## Form fields (draft)

**Plugin name:** `odyssey-engine`

**Repository:** https://github.com/Zhifeng-Niu/odyssey-engine

**Category:** `development`

**Description (short):**
Autonomous iteration engine — loops until data says stop. Metric-driven
waypoints with git checkpoint/rollback, three orientations
(engineer/creative/production), and four convergence tiers
(prototype/standard/production/research) that adapt patience and
stopping thresholds to the project.

**Description (long):**
Odyssey runs autonomous iteration loops that adapt strategy to the task:
code, research, writing, design, data analysis. Each waypoint is
checkpointed to git, verified through a 4-layer pipeline
(syntax → guard → metric → quality), and kept or discarded based on
objective measurement. Convergence is decided by data — average metric
delta over the recent keeps — never by agent self-report. Four delivery
tiers (auto-inferred from tests/CI/changelog/version signals) tune
patience, discard thresholds, and minimum-delta thresholds. Safety
valves: optional time budget, stuck detection with orientation rotation,
protected-file scope, and `/odyssey-cancel`.

**What does it install?**
1 skill, 4 commands, 2 agents, 1 Stop hook (harness-only), 1 stdlib-only
Python helper script. No MCP servers, no network calls, no telemetry.

**Security/self-report checklist:**
- No external network calls (helper is stdlib-only; hook is local bash+python3)
- Stop hook writes only to `.claude/odyssey.local.md` in the project
- Git operations are limited to add/commit/reset on the mission branch
- No secrets handling, no telemetry, no auto-update mechanism

**Homepage:** https://github.com/Zhifeng-Niu/odyssey-engine

**License:** MIT

## Pre-submission checklist

- [x] Installs via `claude plugin marketplace add Zhifeng-Niu/odyssey-engine`
- [x] `claude plugin details odyssey-engine` shows full component inventory
- [x] No hooks outside the mission lifecycle (state-gated on `.claude/odyssey.local.md`)
- [x] Convergence logic covered by runnable checks (see docs/convergence-spec.md)
- [ ] Tag a release: `git tag v1.1.0 && git push origin v1.1.0`
- [ ] Dogfooded once on a real task post-v1.1.0 (recommended before submit)
