# DayQuest Resume Evidence Candidate

Status：`Public Recruiter Surface Published / External CI Verified / Awaiting Independent Competitive Audit and Career Integration`

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
| Engineering controls | Accepted baseline `a1322b2…` passed 196 tests in [GitHub Actions run 33315509118](https://github.com/SakuraLu0001/dayquest-agent/actions/runs/33315509118); recruiter surface `da8dfa8…` passed 200 tests and every artifact/privacy check in [GitHub Actions run 33317902718](https://github.com/SakuraLu0001/dayquest-agent/actions/runs/33317902718) | Public Ubuntu/Python 3.13 evidence; not a production environment matrix |

Stable evidence identities:

- MVP aggregate SHA-256: `10E8D671AD86AF8099820B99E226822799266D0B8F3524377253EDAB94057634`
- Comparison benchmark SHA-256: `769FD95B9161108A5145AF14F5679356DE4B7DE25BBECB5CF4237327A19AE351`
- Product V2 replay canonical SHA-256: `81D0431BD4E9E712D7FFFDE6ACF7E3DF28B03C7A93465120249CE360B5D4F5D3`
- Product V2 fresh-reproduction commit: `598028a983539240126233e23edb1f02b359e03b` (two independent clean clones; raw SHA-256 equals canonical SHA-256 above)
- Frozen historical evidence remains separately versioned: D3 5/5 identities and VS1 3/3 identities match inside the MVP aggregate.

## 10-minute no-key reviewer demo

Prerequisite: Python 3.13 with `requirements.lock.txt` installed. No `.env`, provider login, model download, or external service is required.

1. **00:00–01:00 — state the user problem.** Explain that ordinary activity logs either hide missing evidence or flatten conflicting sources into one story.
2. **01:00–02:00 — verify artifacts.** Run `python -B scripts/run_product_v2.py --check`, `python -B scripts/run_timeline_mvp.py --check`, and `python -B scripts/run_comparison_benchmark.py --check`; point to the three stable identities above.
3. **02:00–05:30 — open the product.** Run `python -B scripts/run_product_v2.py`. On **我的一天 · V2**, show the canonical three-state day and replay the three evidence interventions.
4. **05:30–07:00 — inspect propagation and receipts.** Contrast canonical and preview summaries, show the hypothetical-evidence warning, and open one canonical intervention receipt.
5. **07:00–08:30 — open Evaluation / Review.** Show the 12 cases, zero false-Supported decisions, the separate policy axis, and the mature-project workflow-gap cards.
6. **08:30–09:30 — show reproducibility and privacy controls.** Run `python -B scripts/scan_public_artifacts.py`; point to `requirements.lock.txt`, `SECURITY.md`, and `.github/workflows/ci.yml`.
7. **09:30–10:00 — close with boundaries.** Open the verified public CI run, then state that the test corpus is synthetic-safe; private-data applicability, production reliability, and universal superiority are not claimed.

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
9. Which results are reproduced locally and in public CI, and which user-demonstration or production evidence is still absent?

An independent user demonstration has not yet been recorded. Passing the local technical gates does not answer these questions on behalf of a reviewer.

## Proposed maturity view

`Public resume-flagship technical candidate` is a bounded project status, not an internship-readiness score. MIT, public main, the Product V2 evidence, and the accepted-baseline CI run are directly verified. Independent competitive audit, recruiter demonstration, and formal resume integration remain separate gates; no Release is authorized.

Scope: the current repository and the frozen 12-case synthetic-safe evidence path. Cost: one user-led 10-minute demo plus wording review. Re-estimate if any artifact identity changes, the CI/runtime matrix changes, real-user/private-data scope is proposed, or target roles change.

## Remaining external review gates

- Daily performs an independent, read-only competitive audit against the public evidence.
- The career workflow reviews the local bilingual bullet candidate before placing it into any resume or CV.
- Complete one user-led 10-minute reviewer demo if interview-defense evidence is desired.
- A GitHub Release remains explicitly unauthorized.

## Exact Resume Point

`Hand the public links, visual assets, accepted baseline a1322b21f412bbe72376d575ac84053a7b54982b, recruiter-surface commit da8dfa8241ba2693c54a469c7484cbc4ad90740d, and green run 33317902718 to Daily for independent audit. Do not create a Release or continue Product V2 feature work.`
