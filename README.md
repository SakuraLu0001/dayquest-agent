# DayQuest

DayQuest is a privacy-first agent that reconstructs a synthetic day from fragmented calendar, transaction, and email data, then turns the verified and redacted event skeleton into a fantasy adventure log.

Post-hackathon development plan: [ROADMAP_4_MONTHS.md](ROADMAP_4_MONTHS.md)

DayQuest is a solo Hackathon prototype and is not production-ready.

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
python -m pip install -r requirements.txt
streamlit run app.py
```

Click **Run DayQuest Agent** to view the reconstructed timeline, Privacy Gate, observation-driven loop trace, fantasy story cards, and stop reason.

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

### Mature-project benchmark and DayQuest boundary

| Reference family | Mature capability reused as the baseline | DayQuest's implemented project-specific difference |
|---|---|---|
| OpenAI Evals / UK AISI Inspect | Extensible tasks, datasets, scorers, tool use, multi-turn evaluation | Privacy-safe evidence-carrying timeline claims over a real localhost MCP path |
| Promptfoo | Repeatable automated evaluation, red-team fixtures, metrics and CLI workflows | Stable safe provenance pointers and visible `Supported / Unknown / Conflict` review |
| LangChain AgentEvals | Trajectory and tool-call comparison with ordering and argument controls | Claim evidence and policy compliance remain orthogonal instead of one pass/fail bit |
| METR Task Standard | Versioned tasks, isolated execution and explicit scoring | Conservative synthetic fault cases plus an audit UI that exposes missing and conflicting evidence |

The difference is implemented behavior, not a claim of academic novelty or universal superiority. The reported zero privacy/path-pattern detections applies only to the committed synthetic-safe fixtures and the frozen detector patterns (Windows drive-letter absolute paths, email-shaped text, and Bearer/sk-like token text). It is not private-data validation, general secret scanning, cross-platform path detection, or a security certification. DayQuest also does not yet provide distributed evaluation scale, a production sandbox, live-provider coverage, statistical generalization, an externally executed CI result, or production reliability.

## Verify

```powershell
python -m pytest -q
python -m compileall dayquest app.py scripts
python -B scripts/generate_synthetic_trace.py --check
python -B scripts/run_evaluation_slice.py --check
python -B scripts/run_branch_breadth_slice.py --check
python -B scripts/run_timeline_slice.py --check
python -B scripts/run_timeline_mvp.py --check
```

Tests use fake clients and never call the network. Missing or malformed local sources are reported in the UI while successfully loaded sources remain available.
