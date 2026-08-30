# DayQuest

DayQuest is an epistemic timeline debugger for personal activity evidence. It shows not only what may have happened, but exactly which bounded evidence makes a claim `Supported`, `Unknown`, or `Conflict`; reviewers can replay reversible source/evidence interventions and inspect how claim state and downstream preview summaries change without rewriting the canonical evidence.

```powershell
python -m pip install -r requirements.lock.txt
python -B scripts/run_product_v2.py
```

No API key is required for the evidence-replay UI, 12-case review matrix, or transparent comparison benchmark. Product V2 contains three deterministic interventions: source dropout (`Supported → Unknown`), explicitly hypothetical evidence arrival (`Unknown → Supported` preview only), and conflict-source quarantine (`Conflict → Unknown`, never automatic resolution). Baseline reports and the canonical summary remain immutable. The current local evidence also closes 12/12 expected V1 statuses with 0 false-Supported decisions, preserves 2/2 conflicts, and handles 4/4 controlled tool-failure cases conservatively. These are deterministic synthetic-safe development cases—not production reliability or statistical generalization.

Reviewer pack: [RESUME_EVIDENCE_CANDIDATE.md](RESUME_EVIDENCE_CANDIDATE.md) · Security: [SECURITY.md](SECURITY.md) · License decision: [LICENSE_DECISION.md](LICENSE_DECISION.md)

The repository began as a solo hackathon prototype that reconstructed synthetic calendar, transaction, and email data into a fantasy adventure log. That original provider-backed flow remains available in `app.py`; the no-key evidence timeline is now the primary review path.

Post-hackathon development plan: [ROADMAP_4_MONTHS.md](ROADMAP_4_MONTHS.md)

DayQuest remains a local technical candidate and is not production-ready.

> This demo uses **synthetic data only**. AkashML selects one allowlisted fantasy motif code, Nexla provides normalized events, and Pomerium protects the remote MCP route.

## AkashML integration

Copy `.env.example` to `.env` and provide your AkashML API key. DayQuest sends only an anonymous minimum event structure after the local privacy gate: a generated safe ID, approximate time, event type, redacted summary, and fantasy theme. Original IDs, evidence, email bodies, exact amounts, order numbers, addresses, and local paths are never included in the request.

AkashML returns one of five allowlisted motif codes. The deterministic local renderer uses that code to shape chapter titles, recurring atmosphere, and a fictional embellishment while retaining local event anchors and order. If configuration is missing, the API fails, or the response does not contain exactly one allowed code, DayQuest safely uses the existing fully local generator. `Connected` is shown only after the selected motif influences the final story and local evaluation passes.

## Nexla integration

Nexla Express creates a Source Nexset from the public synthetic JSON dataset. A Nexla Transform then normalizes the heterogeneous calendar, email-metadata, and developer-activity records into the DayQuest Event schema. DayQuest reads those transformed records through the Nexset Samples API and retains only the validated normalized fields.

The short-lived Nexla Session Token is stored only in local environment variables. If the token expires, configuration is missing, the request fails, or a sample fails local schema and privacy validation, DayQuest safely falls back to its existing local synthetic data sources.

## Local MCP privacy gateway

DayQuest exposes three read-only, privacy-safe MCP tools through Streamable HTTP at `http://127.0.0.1:8080/mcp`. The server binds only to localhost. Raw private data is never exposed as an MCP tool.

Start the local server with `python -m dayquest.pomerium_mcp_server`, then run `python -u scripts/pomerium_local_smoke_test.py` in another terminal. Local MCP tool discovery and safe tool invocation passed. Pomerium `pom.run` created an authenticated HTTPS gateway to the local endpoint; a live tunnel was established and an unauthenticated remote request was blocked with HTTP 401. An authenticated remote MCP tool invocation was not completed in the hackathon demo environment, and MCP Inspector was not run.

## Run locally

```powershell
python -m pip install -r requirements.lock.txt
python -B scripts/run_product_v2.py
```

The default local page is the no-key Product V2 surface: **我的一天 · V2** shows the immutable synthetic-safe timeline plus an evidence replay lab. The lab compares before/after claim state, summary propagation, the next evidence action, and a canonical intervention receipt. A hypothetical pointer is always labeled `hypothetical=true`; it may affect the preview but is never promoted to observed evidence or written into the canonical summary. **Evaluation / Review** keeps the 12-case matrix, disclosed ablations, and mature-project workflow-gap comparison separate. Use `streamlit run app.py` only for the original hackathon fantasy-story flow; it may use optional provider configuration.

`requirements.lock.txt` records the exact Python 3.13 environment used for the local evidence run. `requirements.txt` remains the looser development input; reproducible review and CI use the lock. No license has been granted yet: see [LICENSE_DECISION.md](LICENSE_DECISION.md). Security and privacy boundaries are documented in [SECURITY.md](SECURITY.md).

## Structured tool-call trace

Local calendar, transaction, and email reads now emit a machine-readable, privacy-safe trace alongside the existing human-readable Agent Loop Trace. Each JSONL record includes the schema version, run and step identity, tool, status, measured latency, retry attempt, safe error type, state-count transition, and redacted input/output summaries. Raw event payloads, credentials, private fields, email bodies, and absolute local paths are never included.

Generate the deterministic no-key example:

```powershell
python -B scripts/generate_synthetic_trace.py
```

View `artifacts/traces/dayquest-synthetic-baseline-v1.jsonl`. Re-run the byte-stability check with:

```powershell
python -B scripts/generate_synthetic_trace.py --check
```

The stable artifact ID is `dayquest-synthetic-baseline-v1`. This trace is the first evaluation-harness seam: later fault-injection scenarios can compare retry, error, and state transitions without parsing UI prose or exposing private payloads.

## Deterministic evaluation slice

Run the no-key Day 2 development slice:

```powershell
python -B scripts/run_evaluation_slice.py
```

The command executes two versioned local cases: the synthetic success path and one controlled existing `DataLoadError` path. It writes per-case reports under `artifacts/evaluation/day2/reports/` and the exact aggregate receipt to `artifacts/evaluation/day2/aggregate.json`. Verify that committed outputs are byte-stable with `python -B scripts/run_evaluation_slice.py --check`.

The `case_contract_sha256` and aggregate `report_sha256` values are canonical JSON identities, not raw file byte hashes. Their accompanying `case_contract_hash_basis` and `report_hash_basis` fields define the exact basis: parse the JSON, serialize it as UTF-8 with `ensure_ascii=false`, `indent=2`, `sort_keys=true`, and one trailing LF newline, then calculate SHA-256. Different source whitespace or key order can therefore have the same canonical identity while retaining different raw byte hashes.

The checker keeps record validity, policy compliance, and terminal-claim support separate. A removed necessary trace event becomes `unknown`; contradictory evidence becomes `failed`. This two-case artifact is a development slice, not the final DayQuest benchmark or a statistical performance claim.

### Branch-breadth development slice

Run the no-key five-case slice, which retains the two accepted Day 2 reports and adds three existing-branch fixtures:

```powershell
python -B scripts/run_branch_breadth_slice.py
```

The added cases cover categorized Nexla failure followed by successful local fallback, the existing maximum-iteration safe stop, and an intentionally injected unexpected-retry policy contradiction. The last case is a harness self-test/fault fixture: it proves that a policy violation is counted as `failed`, not `supported`; it is not a product failure-rate observation. Reports are written under `artifacts/evaluation/day3/reports/`, with the exact aggregate at `artifacts/evaluation/day3/aggregate.json`. All new contract and report identities use the same canonical JSON hash basis documented above.

This branch-breadth artifact remains a deterministic development slice. It is not a final benchmark or statistical performance claim, and it does not add runtime retry behavior.

## Evidence-carrying timeline vertical slice

Run the no-key Top-1 VS1 slice:

```powershell
python -B scripts/run_timeline_slice.py
```

The command starts the repository's real localhost FastMCP process, opens a Streamable HTTP client session, calls the read-only safe-event tool with `local_only=true`, and then stops and reaps the child process. It writes two versioned reports and one aggregate receipt under `artifacts/evaluation/top1/vs1/`.

`DQ-TOP1-POSITIVE-001` carries the complete synthetic-safe calendar and email evidence for one focal claim and must be `Supported` with source pointers. `DQ-TOP1-MISSING-001` changes only the bounded event view so that the required calendar evidence is absent; it must be `Unknown`, never falsely `Supported`. Verify committed outputs through the same real transport with `python -B scripts/run_timeline_slice.py --check`.

Source pointers use `dayquest.safe_event_identity.v1`. Each `safe-v1-...` ID is the full SHA-256 of UTF-8 canonical JSON containing only the identity schema, source, event type, approximate time, and already privacy-safe summary (`ensure_ascii=false`, sorted keys, compact separators). The identity therefore does not depend on list position, query limit, return order, process lifetime, raw event ID, exact timestamp, local path, or a secret. This is a stable identity for an already allowed safe projection, not encryption or proof of anonymization; an identity collision fails closed.

That VS1 artifact remains a two-case localhost development slice; its original scope does not implement `Conflict`, exercise private data or remote providers, establish production reliability, or complete the Top-1 case matrix. The accepted MVP below extends it without rewriting those historical outputs.

## Evidence review MVP

Launch the no-key 12-case product review flow:

```powershell
python -B scripts/run_timeline_mvp.py
```

The command first reproduces and checks every committed report, then opens a local Streamlit review surface. Eight cases perform real localhost MCP acquisition: five use the MCP response as the final scenario evidence without modification, while three (`MISSING-002`, `CONFLICT-001`, and `CONFLICT-002`) apply an explicit controlled post-MCP transform to create the missing/conflicting condition. The remaining four cases are controlled tool-fault fixtures and do not claim real MCP acquisition. The matrix contains three `Supported`, seven `Unknown`, and two `Conflict` focal claims, while policy compliance remains a separate axis. A story receives factual input only when the claim is `Supported` and policy is compliant.

Reviewers can inspect supporting pointers, contradicting pointers, missing requirements, policy violations, tool-safe outcomes, and story eligibility without reading raw JSON. Verify the committed artifacts without opening the UI with `python -B scripts/run_timeline_mvp.py --check`.

The corrected evidence-lineage and scoped privacy structures are versioned as `dayquest.timeline_mvp_report.v2` and `dayquest.timeline_mvp_aggregate.v2`. Case contracts are unchanged: the two reused VS1 contracts remain `dayquest.timeline_task_case.v1`, and the ten MVP contracts remain `dayquest.timeline_task_case.v2`.

## Product V2 evidence replay

Generate or verify the deterministic replay artifact without opening the UI:

```powershell
python -B scripts/run_product_v2.py --generate
python -B scripts/run_product_v2.py --check
```

The committed artifact is `artifacts/product_v2/replay_demo.json`. Each replay binds the original V1 report by canonical SHA-256, records the evidence operation and before/after state, and issues a stable `dayquest.intervention_receipt.v1` receipt. The three interventions are previews only:

- removing an observed email confirmation makes the language-exam claim `Supported → Unknown`;
- adding an explicitly hypothetical calendar pointer previews the hackathon claim as `Unknown → Supported`, but requires a real read-only source check before any promotion;
- quarantining the Riverside location contradiction makes the location claim `Conflict → Unknown`, because removing a conflict does not prove the remaining source.

The canonical timeline and summary are never modified by replay. Product V2 does not claim causal inference, private-data compatibility, production reliability, statistical generalization, or performance superiority over mature projects.

### Mature-project workflow gap and DayQuest boundary

The competitive audit fixes exact public commit identities in `DAYQUEST_PRODUCT_V2_COMPETITIVE_AUDIT.md`. The executable Product V2 artifact carries a compact comparison against ActivityWatch, screenpipe, DailyOS, Langfuse, and Phoenix. Those projects already cover mature local capture/timeline/search or trace/evaluation workflows. DayQuest V2 therefore does not present “local-first”, “timeline”, “source references”, or “evaluation UI” as its unique value; it focuses on reversible evidence interventions, explicit epistemic-state transitions, conservative summary propagation, and receipts bound to immutable baseline reports.

This is a documentation / architecture / public-workflow comparison only. Third-party repositories were not installed or executed, and no performance or maturity comparison is claimed. The implemented difference is a bounded project position, not academic novelty or universal superiority. The reported zero privacy/path-pattern detections applies only to the committed synthetic-safe fixtures and the frozen detector patterns (Windows drive-letter absolute paths, email-shaped text, and Bearer/sk-like token text). It is not private-data validation, general secret scanning, cross-platform path detection, or a security certification. DayQuest also does not yet provide distributed evaluation scale, a production sandbox, live-provider coverage, statistical generalization, an externally executed CI result, or production reliability.

### Transparent comparison benchmark

Run the deterministic comparison on the same committed 12-case matrix:

```powershell
python -B scripts/run_comparison_benchmark.py --check
```

The benchmark compares the implemented DayQuest evidence gate with three deliberately simple, fully disclosed ablations: summarizing every non-Unknown claim, letting any support override missing or contradictory evidence, and promoting tool-failure cases to completion. These are diagnostic reference strategies, not reproductions of mature competing products. The artifact records each rule, tradeoff, per-case decision, and metric definition at `artifacts/evaluation/comparison/benchmark.json`.

On this fixed synthetic-safe matrix, DayQuest preserves both conflicts, keeps all four tool-failure cases conservative, emits no unsupported summary facts, and produces zero false-Supported decisions. The claim is limited to these 12 deterministic development cases; it is not a statistical benchmark, real-user study, production reliability claim, or universal superiority result. Observed local execution time is printed by the runner but excluded from the canonical artifact identity.

## Verify

```powershell
python -m pytest -q
python -m compileall dayquest app.py scripts
python -B scripts/generate_synthetic_trace.py --check
python -B scripts/run_evaluation_slice.py --check
python -B scripts/run_branch_breadth_slice.py --check
python -B scripts/run_timeline_slice.py --check
python -B scripts/run_timeline_mvp.py --check
python -B scripts/run_comparison_benchmark.py --check
python -B scripts/run_product_v2.py --check
python -B scripts/scan_public_artifacts.py
```

Tests use fake clients and never call the network. Missing or malformed local sources are reported in the UI while successfully loaded sources remain available.

The checked-in GitHub Actions workflow is **Configured / Not Yet Externally Executed** in this local-only phase. A green local run does not claim that GitHub Actions has passed; that evidence can exist only after a separately authorized push.
