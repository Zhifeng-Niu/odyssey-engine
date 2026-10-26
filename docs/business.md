# Odyssey Business Charter v0.1 (2026-10-26)

Companion to the machine (this repo), the architecture (architecture.md),
and the language North Star. This document is the company, not the code.

## 1. The category claim

**"Governance & Economics for Agent Labor"** — agent 时代的 FinOps + SRE.

Cloud had a cost crisis → FinOps category (Vantage/CloudZero, $1B+ outcomes).
Agents are entering the same crisis, worse: agent spend is **unbounded by
design** (loops that don't know when to stop) and **unverifiable by
default** (no evidence trail). The budget line is emerging 2026–2028 as
agent deployments move from demo to production.

We own the stopping problem: **when to stop, what it cost, what it
provably achieved.** Core metric we evangelize: **$ per verified outcome**.

## 2. Product stratification (open-core)

| Tier | What | Price | Buyer |
|------|------|-------|-------|
| OSS core (MIT) | loop, convergence engine, fields, arsenal | free | developers |
| Pro | hosted missions, dashboards, benchmark reports | ~$29–99/mo | prosumers, consultants, MBA-types |
| Enterprise | governance policies (budget caps, stop policies, audit trails), private-model adapters, compliance exports | $20–50k/yr ACV | teams running agents on domestic models at scale |

OSS is not a loss leader; it is distribution, trust, and the corpus
flywheel (100-mission evidence base doubles as sales material).

## 3. Why defensible (and why not)

Defensibility:
- **Convergence IP**: 5 weeks of shipped, tested, battle-hardened stop
  semantics (pivot partitioning, drift probes, churn fuse) — no market
  equivalent; incumbents (LangChain et al.) have orchestration, not
  epistemology.
- **Model neutrality**: Western tooling defaults to flagship models; the
  amplifier theorem is *for* GLM/DeepSeek/Qwen deployments — the exact
  segment Anthropic/OpenAI will never prioritize.
- **Architecture charter**: public seven-layer contracts invite
  re-implementation; standards capture value at the governance layer.

Attack surfaces (be honest):
- Datadog-class observability vendors can bolt on "agent governance".
  Counter: they monitor; we *decide* (stop semantics are control-plane,
  not data-plane). Speed is the only defense.
- Foundation models absorbing loop scaffolding. Counter: neutrality —
  governance that stops at one vendor's border is not governance.

## 4. GTM wedge sequencing

1. **Wedge (0–6 mo)**: decision-intelligence missions (strategy field,
   Chinese-speaking consultants/MBA/ops teams). Not the company — the
   beachhead. First 10 paying Pro users from the founder's content
   distribution (公众号 = built-in channel).
2. **Proof (6–12 mo)**: 3 lighthouse enterprise pilots running governance
   on domestic-model agent fleets. Free pilots → paid conversion → case
   studies. Publish the amplifier benchmark publicly (GLM bare vs
   GLM+odyssey) — content is the moat-compounder.
3. **Scale (12–24 mo)**: category evangelism ($/verified-outcome),
   platform partnerships (Orca-class harnesses embedding layer 3),
   compliance angle for China enterprise (算法审计轨迹 exports).

## 5. Financing map (milestones, not rounds)

| Capital event | Unlock condition | Approx. |
|---------------|------------------|---------|
| Bootstrap | wedge revenue ≥ ¥50k/mo | now–6mo |
| Pre-seed/seed | 3 enterprise pilots signed, $100k ARR line-of-sight | 6–12mo |
| Series A | $1M ARR, category metric cited by non-customers | 24–36mo |

Rule: no fundraising before the falsifiable milestone — first external
team *paying* for the convergence layer. Capital before proof buys
obligations, not speed.

## 6. What NOT to do

- No horizontal harness war (Orca/Cline territory — funded armies).
- No model training, no infra, no marketplace.
- No enterprise custom services that don't productize.
- No "AI strategy consulting" trap — the MBA network is a channel, not
  the business.

## 7. Founder leverage (why now, why me)

- Machine: 6 weeks from broken plugin → v1.5.3 (40 tests) + three
  charters — demonstrated build velocity solo.
- Distribution: content platform reaches the exact Chinese AI-operations
  audience; MBA cohort = future buyers with procurement influence.
- Corpus: every real mission (starting with the factory-layout strategy
  mission) is simultaneously product, case study, and language corpus.

## 8. Next 90 days (parallel to MBA)

1. Official marketplace submission (docs/marketplace-submission.md) +
   first 10 real missions logged.
2. Amplifier benchmark published (GLM bare vs GLM+odyssey, same task).
3. First design partner signed from content community (free → data).
4. $/verified-outcome defined and evangelized in one flagship essay.

The unicorn question is not "can odyssey be worth $1B" — it is "can this
category exist and can we own its vocabulary when it does." The machine
is running. The next milestone is a paying stranger.
