# Model-Adaptive Harness Spec

## Thesis

The same model performs differently under different harnesses. Scaffolding
is a capability multiplier: a non-flagship model under a disciplined
harness can outperform a flagship model under none. Odyssey's mission is
to raise that floor — to make agent value a property of the *system*
(model + harness), not of the model alone.

## The amplifier theorem

```
progress = attempts × keep-rate × average-gain(kept waypoints)
```

Weak models lose on all three terms: they give up early (few attempts),
claim completion falsely (low keep-rate fidelity — discards masquerade as
keeps), and drift across steps (low average gain). Odyssey externalizes
the three corresponding faculties:

| Model weakness | External prosthesis |
|----------------|---------------------|
| Gives up early | Stop hook — persistence is structural, exit is impossible mid-mission |
| Self-assessment is dishonest | Convergence decided by data (`convergence-check`), never by agent report |
| Procedure decays over long horizons | Full waypoint prompt re-injected every turn + MISSION.md as external memory |

The filter (keep/discard by measurement) converts a high error rate into
net progress; the hook converts a low attempt rate into volume. That
combination is what lets cheap models do serious work: **volume is free
when verification is honest.**

## Model classes (v1.5.0, shipped)

`--model-class flagship|standard|compact`, stored in state, scales
waypoint-prompt density:

- **compact** — full scaffold + micro-discipline: smallest-step rule
  (one file/function), edit→verify after every edit, two-strikes-then-
  switch, deterministic compass (backlog order by confidence, no
  open-ended divergence)
- **standard** — the full 8-step waypoint procedure (default)
- **flagship** — terse brief (counters + one-line directive); the model
  re-derives procedure, saving tokens and scaffolding friction

Agent-side compass granularity: compact → single-file hypotheses and
Arsenal preference over invention; flagship → may batch tightly-related
edits, creative divergence encouraged.

Tier interaction: cheap attempts are safe attempts. For `compact`,
prefer patience-heavy tiers and accept smaller deltas — verification
does the filtering, volume is free.

## Roadmap

- **Auto class inference**: measure the model instead of asking (probe:
  self-consistency across N runs, instruction retention over horizon) —
  replace the flag with a calibration waypoint at mission start
- **Per-class tier scaling**: derived tiers (compact×standard →
  patience +50%, min_delta −30%)
- **Class-stratified evals**: `claude plugin eval` arms per model class,
  so harness improvements are measured as floor-raising, not
  flagship-flattering
- **DELIB layer** (see convergence-spec.md): deliberation ontology —
  benefits disproportionately from strong models; queues after this
