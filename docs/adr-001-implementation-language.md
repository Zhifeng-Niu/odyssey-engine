# ADR-001: Implementation Language for the Engine Core

Status: Accepted (2026-10-26)
Context: v1.5.1 / v1.5.2 — two real incidents of shell string handling
killing multibyte missions (BSD sed + C locale → "RE error: illegal byte
sequence"; sed delimiter injection on user content).

## Decision

1. The CC plugin stays **bash (glue) + Python 3 stdlib (logic)**. Bash
   never touches user content — doctrine: *no sed, no user string through
   shell substitution; python with explicit `encoding="utf-8"` only.*
2. When the convergence layer is extracted (convergence-spec.md, v2), the
   standalone artifact is implemented in **Go as a single static binary**,
   with the Python version kept as the reference implementation. Both run
   the same test corpus; verdicts must match byte-for-byte.

## Rationale

- The plugin's distribution form is a cloned directory. Zero-install,
  zero-build beats every other property; Python stdlib is the only option
  with both.
- The bug class that motivated this ADR (locale-dependent string
  handling) is closed by doctrine + regression tests, not by language.
- A standalone convergence binary targets users *outside* CC (any
  harness, CI jobs) — there, a static cross-platform binary is the right
  distribution, and Go's compile-and-forget toolchain suits a
  part-time-maintained project better than Rust's iteration cost.

## Trigger conditions for revisiting

- A **third** encoding/locale incident in the plugin (doctrine failed) →
  port the plugin's helper to Go ahead of the v2 schedule.
- The **first external contributor** to the helper → Go port moves up
  (typed schemas lower review burden for strangers).

## Alternatives considered

- Rust: strongest guarantees; iteration cost too high for the maintenance
  budget. Revisit only if the binary grows parsing-critical logic.
- TypeScript/Bun: same ecosystem as CC, but adds a runtime dependency
  (or large bun-compiled artifacts) without solving anything Python
  doesn't already.
