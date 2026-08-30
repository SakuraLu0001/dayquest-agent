# DayQuest Resume Evidence Candidate

Status：`Local Technical Candidate / Awaiting User Review`

This is a review pack, not a final resume bullet, publication approval, open-source release, or hiring-readiness claim.

## 30-second project case

DayQuest is a provenance-first daily timeline reconstructor. It converts bounded local MCP evidence into a readable “my day” view while preserving `Supported / Unknown / Conflict`, keeping evidence sufficiency separate from policy compliance, and preventing unsupported or conflicted claims from becoming summary facts.

The differentiator is implemented behavior rather than a framework choice: a reviewer can inspect supporting evidence, contradictory evidence, missing requirements, tool-failure handling, and the summary gate through one no-key local UI.

## Evidence closed locally

| Claim | Local evidence | Boundary |
|---|---|---|
| Product-first timeline | `timeline_app.py` defaults to **我的一天** with one complete synthetic-safe day | Not tested with private user data |
| Three-state review | 1 Supported, 1 Unknown, 1 Conflict in the product demo; complete 12-case matrix is 3 / 7 / 2 | Fixed deterministic development cases |
| Conservative summary | Only Supported + policy-compliant facts are eligible; leakage 0/12 | Does not establish natural-language model reliability |
| Conflict handling | 2/2 expected conflicts preserved with both evidence roles | Bounded fixture conflicts |
| Tool-failure safety | 4/4 controlled tool-failure cases remain conservative | No production fault-rate claim |
| False support | 0 false-Supported decisions across the 12-case matrix | No statistical generalization |
| Transparent comparison | Same 12 cases compared with three disclosed ablations | Ablations are not mature competitor implementations |
| Reproducibility | Two fresh-directory runs reproduced identical MVP and comparison identities | Uses the already available Python 3.13 runtime |
| Engineering controls | 182 local tests, exact dependency lock, scoped privacy scan, CI workflow configured | GitHub Actions not externally executed |

Stable evidence identities:

- MVP aggregate SHA-256: `10E8D671AD86AF8099820B99E226822799266D0B8F3524377253EDAB94057634`
- Comparison benchmark SHA-256: `769FD95B9161108A5145AF14F5679356DE4B7DE25BBECB5CF4237327A19AE351`
- Frozen historical evidence remains separately versioned: D3 5/5 identities and VS1 3/3 identities match inside the MVP aggregate.

## 10-minute no-key reviewer demo

Prerequisite: Python 3.13 with `requirements.lock.txt` installed. No `.env`, provider login, model download, or external service is required.

1. **00:00–01:00 — state the user problem.** Explain that ordinary activity logs either hide missing evidence or flatten conflicting sources into one story.
2. **01:00–02:00 — verify artifacts.** Run `python -B scripts/run_timeline_mvp.py --check` and `python -B scripts/run_comparison_benchmark.py --check`; point to the two stable hashes above.
3. **02:00–05:00 — open the product.** Run `python -B scripts/run_timeline_mvp.py`. On **我的一天**, show the Supported morning event, the Unknown evening event and its missing requirement, and the Conflict location with both evidence sides.
4. **05:00–06:30 — inspect the summary gate.** Show that only the Supported + compliant event enters the constrained summary.
5. **06:30–08:30 — open Evaluation / Review.** Show 12 cases, zero false-Supported decisions, the separate policy axis, and the comparison table.
6. **08:30–09:30 — show reproducibility and privacy controls.** Run `python -B scripts/scan_public_artifacts.py`; point to `requirements.lock.txt`, `SECURITY.md`, and `.github/workflows/ci.yml`.
7. **09:30–10:00 — close with boundaries.** State that the evidence is local and synthetic-safe; CI is configured but not externally executed; private-data applicability, production reliability, and universal superiority are not claimed.

Stop the Streamlit process after review. Do not enter credentials or switch to a provider-backed path during this demo.

## Independent reviewer questions

A reviewer should be able to answer without reading source code:

1. Which event is a fact and why?
2. Which event is Unknown and exactly what evidence is missing?
3. Which event is Conflict and where are the two evidence sides?
4. Why does a policy violation remain separate from claim status?
5. Why does the summary exclude Unknown, Conflict, and non-compliant claims?
6. What do the three reference strategies assume, and where do they fail?
7. Which result is locally reproduced, and which external/public evidence is still absent?

An independent user demonstration has not yet been recorded. Passing the local technical gates does not answer these questions on behalf of a reviewer.

## Proposed maturity view

`80% local technical candidate evidence` is a provisional review heuristic, not a governance fact or internship-readiness score. Basis: 8 of the 10 proposed gates in `DAYQUEST_RESUME_COMPETITIVENESS_CONTRACT.md` have local technical evidence. Gate 9 still needs an independent user/reviewer demonstration; Gate 10 intentionally remains pending because final resume wording, license choice, push, release, and publication require separate user decisions.

Scope: the current repository and the frozen 12-case synthetic-safe evidence path. Cost: one user-led 10-minute demo plus publication decisions. Re-estimate if any artifact identity changes, an external CI run occurs, real-user/private-data scope is proposed, or target roles change.

## Remaining public-readiness gates

- User reviews this candidate pack and performs or delegates one independent 10-minute demo.
- User chooses MIT, Apache-2.0, or no publication; `LICENSE_DECISION.md` is not a license.
- User separately authorizes final resume wording, repository push, public visibility, release, or external CI.
- Before publication, confirm repository history and assets contain no unapproved private material and review third-party licenses.

## Exact Resume Point

`Await user review of RESUME_EVIDENCE_CANDIDATE.md and one independent no-key 10-minute demo; do not write the final resume bullet, add LICENSE, push, release, or claim external CI until separately authorized.`
