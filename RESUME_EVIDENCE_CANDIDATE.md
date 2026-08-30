# DayQuest Resume Evidence Candidate

Status：`Product V2 Local Technical Candidate / Publication Authorized / Awaiting External CI`

This is a review pack, not a final resume bullet, publication approval, open-source release, or hiring-readiness claim.

## 30-second project case

DayQuest is an epistemic timeline debugger for personal activity evidence. It preserves `Supported / Unknown / Conflict`, then lets a reviewer replay reversible source/evidence interventions and inspect how claim state and preview summaries change without rewriting the canonical evidence.

The bounded project differentiator is implemented behavior rather than a framework choice: a reviewer can remove, hypothetically add, or quarantine one evidence pointer, inspect a stable intervention receipt, and see the conservative next evidence action through one no-key local UI.

## Evidence closed locally

| Claim | Local evidence | Boundary |
|---|---|---|
| Product-first timeline | `timeline_app.py` defaults to **我的一天** with one complete synthetic-safe day | Not tested with private user data |
| Epistemic evidence replay | 3 deterministic previews cover `Supported → Unknown`, `Unknown → Supported`, and `Conflict → Unknown` | Preview only; no causal or real-user inference |
| Immutable evidence boundary | Replay receipts bind canonical V1 report identities; baseline reports and canonical summary stay unchanged | Does not implement an observed-evidence promotion workflow |
| Three-state review | 1 Supported, 1 Unknown, 1 Conflict in the product demo; complete 12-case matrix is 3 / 7 / 2 | Fixed deterministic development cases |
| Conservative summary | Only Supported + policy-compliant facts are eligible; leakage 0/12 | Does not establish natural-language model reliability |
| Conflict handling | 2/2 expected conflicts preserved with both evidence roles | Bounded fixture conflicts |
| Tool-failure safety | 4/4 controlled tool-failure cases remain conservative | No production fault-rate claim |
| False support | 0 false-Supported decisions across the 12-case matrix | No statistical generalization |
| Transparent comparison | Same 12 cases compared with three disclosed ablations | Ablations are not mature competitor implementations |
| Reproducibility | Two independent clones reproduced identical raw and canonical Product V2 identities; prior MVP/comparison fresh runs remain closed | Uses the already available Python 3.13 runtime |
| Engineering controls | 196 local tests, exact dependency lock, LF-pinned evidence artifacts, scoped privacy scan, CI workflow configured | GitHub Actions not externally executed |

Stable evidence identities:

- MVP aggregate SHA-256: `10E8D671AD86AF8099820B99E226822799266D0B8F3524377253EDAB94057634`
- Comparison benchmark SHA-256: `769FD95B9161108A5145AF14F5679356DE4B7DE25BBECB5CF4237327A19AE351`
- Product V2 replay canonical SHA-256: `81D0431BD4E9E712D7FFFDE6ACF7E3DF28B03C7A93465120249CE360B5D4F5D3`
- Product V2 fresh-reproduction commit: `598028a983539240126233e23edb1f02b359e03b` (two independent clean clones; raw SHA-256 equals canonical SHA-256 above)
- Frozen historical evidence remains separately versioned: D3 5/5 identities and VS1 3/3 identities match inside the MVP aggregate.

## 10-minute no-key reviewer demo

Prerequisite: Python 3.13 with `requirements.lock.txt` installed. No `.env`, provider login, model download, or external service is required.

1. **00:00–01:00 — state the user problem.** Explain that ordinary activity logs either hide missing evidence or flatten conflicting sources into one story.
2. **01:00–02:00 — verify artifacts.** Run `python -B scripts/run_product_v2.py --check` and point to the stable replay identity above.
3. **02:00–05:30 — open the product.** Run `python -B scripts/run_product_v2.py`. On **我的一天 · V2**, show the canonical three-state day and replay the three evidence interventions.
4. **05:30–07:00 — inspect propagation and receipts.** Contrast canonical and preview summaries, show the hypothetical-evidence warning, and open one canonical intervention receipt.
5. **07:00–08:30 — open Evaluation / Review.** Show the 12 cases, zero false-Supported decisions, the separate policy axis, and the mature-project workflow-gap cards.
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
6. Why does hypothetical evidence change only the preview, and what would be required before promotion?
7. Why does quarantining a conflicting pointer produce Unknown rather than Supported?
8. What do the three reference strategies assume, and where do they fail?
9. Which result is locally reproduced, and which external/public evidence is still absent?

An independent user demonstration has not yet been recorded. Passing the local technical gates does not answer these questions on behalf of a reviewer.

## Proposed maturity view

`Local technical candidate evidence complete` is a bounded project status, not an internship-readiness score. The user has authorized MIT and the public push. External CI, public-surface verification, and final wording review remain separate evidence gates; no Release is authorized.

Scope: the current repository and the frozen 12-case synthetic-safe evidence path. Cost: one user-led 10-minute demo plus publication decisions. Re-estimate if any artifact identity changes, an external CI run occurs, real-user/private-data scope is proposed, or target roles change.

## Remaining public-readiness gates

- Push the authorized MIT/publication commit to the existing public `origin/main` without force.
- Verify the actual GitHub Actions conclusion and the public Product V2 README/artifact identity.
- Review the local-only resume bullet draft against the public evidence.
- A GitHub Release remains explicitly unauthorized.

## Exact Resume Point

`Push the authorized main branch, verify external CI and public Product V2 evidence, then review the local-only resume bullet draft. Do not create a Release.`
