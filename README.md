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

## Verify

```powershell
python -m pytest -q
python -m compileall dayquest app.py scripts
```

Tests use fake clients and never call the network. Missing or malformed local sources are reported in the UI while successfully loaded sources remain available.
