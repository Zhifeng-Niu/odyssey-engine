# The Odyssey Intelligence Stack (Architecture Charter, v0.1)

An architecture is not a product; it is a **vocabulary other systems can
implement**. This charter names the seven layers odyssey has grown, states
each layer's contract, and defines what it takes for the stack to become a
standard rather than a project.

## The layers

Each layer answers one question. Interfaces between layers are typed
artifacts (waypoint records, verdicts, graphs) — never prose.

| # | Layer | Question | Contract (input → output) | Status |
|---|-------|----------|---------------------------|--------|
| 1 | **Attempt** 行动 | How to act | hypothesis → artifact + measurement | ✅ shipped |
| 2 | **Evidence** 证据 | What actually happened | artifact → typed waypoint records (jsonl) | ✅ shipped |
| 3 | **Metacognition** 元认知 | Should this continue | evidence + profile → verdict (continue/converged/stuck/stale/churn) | ✅ shipped — no market equivalent |
| 4 | **Deliberation** 审议 | Is the question right | evidence graph → pivot / reframe | 🟡 specified (convergence-spec) |
| 5 | **Values** 价值 | What must not be traded | criteria (weighted + lexical) → veto gates | 🟡 specified |
| 6 | **Adaptation** 适应 | What is running | model/field/tier → harness density + compass granularity | ✅ shipped (v1.5.0) |
| 7 | **Governance** 治理 | Who pays, who is accountable | budgets + audit trail → policy verdicts | 🟡 partial (time budget, jsonl audit) |

Layer 3 is the crown: every existing agent framework has layers 1–2;
nobody ships a credible, data-driven answer to "when should an agent
stop, and is the *question itself* still valid".

## What this is NOT

- Not an orchestration framework (LangChain's territory — plumbing).
- Not a cognitive architecture in the SOAR/ACT-R sense (pre-LLM symbolic
  cognition). The stack is **empirical**: its "type system" is measured
  evidence, its "termination semantics" is convergence.
- Not a model. Layers are model-agnostic by contract — that is the
  amplifier theorem applied to architecture.

## Explicit gaps (v2 candidates or declared non-goals)

- **Memory** across missions (cross-mission learning) — candidate layer 8.
- **Multi-agent protocols** (the Board models them; protocols for running
  them are open).
- **Perception grounding** — declared non-goal; the stack assumes a
  measurement function exists (layer 2's `measure:` contract).

## Standardization path

Architectures become standards by being re-implemented, not by being
adopted:

1. **Spec-first**: each layer's contract lives in a versioned doc
   (convergence-spec.md is layer 3's; this file is the index).
2. **Reference implementation**: the Python engine (this repo), portable
   core planned as a static binary (ADR-001).
3. **Third-party implementations**: the existing falsifiable criterion —
   3 external harnesses implementing layer 3's verdict contract.
4. **Corpus**: 100 real missions as the stack's evidence base.

## Relationship to the other charters

- The **language** (user North Star) expresses programs *for* this stack.
- The **company** (governance layer, "FinOps for agent labor") sells
  managed implementations of layers 3 + 7. Architecture is the moat for
  the business, not a separate ambition.
