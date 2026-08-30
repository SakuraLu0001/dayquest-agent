# DayQuest Public Evidence Receipt

Status: `Verified / Public Main / External CI Green / Awaiting Resume Wording Review`

Verification date: `2026-08-30`

## Bound public evidence

- Repository: <https://github.com/SakuraLu0001/dayquest-agent>
- Visibility: `PUBLIC`
- Default branch: `main`
- Evidence-bearing commit: `ab3a69b1637ebbba5bc69a11c300dc92fe3ffa50`
- External workflow: [GitHub Actions run 33315185898](https://github.com/SakuraLu0001/dayquest-agent/actions/runs/33315185898)
- Workflow conclusion: `success`; one Ubuntu job completed in 43 seconds.
- License: GitHub detected `MIT`; the public root `LICENSE` is the standard MIT text for `Copyright (c) 2026 Liyang Luo`.
- Release state: no GitHub Release existed at verification, and none was authorized or created.

## Checks observed in the green job

The job installed `requirements.lock.txt`, passed the 196-test matrix, then passed the committed checks for the synthetic trace, Day 2 evaluation slice, Day 3 branch-breadth slice, timeline vertical slice, 12-case timeline MVP, comparison benchmark, Product V2 replay, and scoped public-artifact scan.

The run emitted one maintenance annotation: `actions/checkout@v4` and `actions/setup-python@v5` still target Node.js 20 and GitHub currently forces them onto Node.js 24. The job passed; this is a future workflow-maintenance signal, not evidence of a DayQuest product failure.

## Stable product evidence

- Product V2 replay canonical SHA-256: `81D0431BD4E9E712D7FFFDE6ACF7E3DF28B03C7A93465120249CE360B5D4F5D3`
- MVP aggregate SHA-256: `10E8D671AD86AF8099820B99E226822799266D0B8F3524377253EDAB94057634`
- Comparison benchmark SHA-256: `769FD95B9161108A5145AF14F5679356DE4B7DE25BBECB5CF4237327A19AE351`
- Frozen development matrix: 12/12 expected statuses, 0 false-Supported decisions, 2/2 conflicts preserved, and 4/4 controlled tool-failure cases handled conservatively.

## Public-surface boundary

The public README exposes Product V2, the no-key launch path, stable identities, 12-case evidence, and explicit claim limits. The GitHub About description still uses the original fantasy-story positioning. That metadata was inspected but not changed because repository-metadata editing was not authorized.

This receipt supports a bounded public technical-candidate claim. It does not establish production reliability, statistical generalization, private-data safety, security certification, academic novelty, mature-project superiority, internship readiness, or independent user mastery. The local resume draft remains outside Git and awaits user wording review. No Release is authorized.

## Resume Point

`Review RESUME_BULLET_DRAFT.local.md against this receipt and the public run. Separately authorize any GitHub About-description change. Do not create a Release.`
