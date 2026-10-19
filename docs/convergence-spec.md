# Convergence Layer Spec (v2 direction)

## Thesis

Loop runners are commoditized (ralph-loop, autodev, Orca automations,
odyssey itself). **Stopping criteria are not.** No mainstream runner decides
"when to stop" from objective measurement — they run on fixed counts, or on
the model's say-so. The convergence engine inside odyssey
(`odyssey_helper.py`) is the asset; the loop is just one host for it.

This spec extracts convergence into a standalone, loop-agnostic layer.

## Contract

Any iterating process (agent loop, CI job, human workflow) produces
**waypoint records**; the layer returns a **verdict**.

```
waypoint record (one JSON line):
{
  "run": 7,                      # monotonically increasing
  "status": "keep" | "discard",  # was this attempt retained?
  "metric": 182.4,               # primary measurement (float)
  "secondaryMetrics": {...},     # optional
  "note": "connection pooling"   # optional
}

verdict (stdout JSON):
{
  "verdict": "continue" | "converged" | "stuck",
  "confidence": "high" | "low",
  "reason": "avg delta 0.075% < 0.5% over last 5 keeps",
  "evidence": [ ...per-check results... ],
  "suggestion": "rotate-orientation" | null
}
```

Guarantees:
- stdlib-only, zero deps, single file (`convergence.py`)
- deterministic: same records + profile ⇒ same verdict
- the layer NEVER mutates caller state; callers own keep/discard

## Profiles as data

Tiers are the unit of tuning. v2 moves them from hardcoded dicts to a
versioned profile document so users can ship project-local overrides:

```yaml
# .convergence.yaml
tier: production            # or infer: true
patience: 50
discard_threshold: 15
min_delta_pct: 0.1
window: 5
on_stuck: ask               # ask | rotate | stop
```

Inference rules (tests/CI/changelog/version/docs → tier) stay in the layer
so every host benefits from improvements to the heuristic.

## Hosts

| Host | Integration |
|------|-------------|
| odyssey-engine | embeds the layer (current behavior, unchanged UX) |
| any stop-hook loop | call `convergence.py check --jsonl …` before re-prompt |
| Orca automations | automation step runs the check; `stuck` ⇒ spawn review |
| CI | nightly job: verdict on a metrics JSONL ⇒ gate promotion |

## Roadmap

- **v1.1 (shipped)**: convergence correct inside odyssey; hook emission fixed
- **v1.2**: rename/extract to `convergence.py` with the verdict contract above;
  odyssey's helper becomes a thin wrapper; add `.convergence.yaml`
- **v1.3**: worktree-native mode — waypoint = isolated worktree instead of
  commit/reset on the main checkout (post-Orca safety model)
- **v2**: non-code metric adapters (research corpora, writing quality proxies,
  data-analysis benchmarks) — the original "not just code" promise, now
  actually measurable

## What this is not

Not a runner. Not a daemon. No hooks of its own. It answers one question —
*"given the evidence, should this loop keep going?"* — and answers it
the only defensible way: from the data.
