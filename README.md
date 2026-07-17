# DayQuest

DayQuest is a privacy-first agent that reconstructs a synthetic day from fragmented calendar, transaction, and email data, then turns the verified and redacted event skeleton into a fantasy adventure log.

> This demo uses **synthetic data only**. AkashML selects one allowlisted fantasy motif code; Nexla and Pomerium are not connected.

## AkashML integration

Copy `.env.example` to `.env` and provide your AkashML API key. DayQuest sends only an anonymous minimum event structure after the local privacy gate: a generated safe ID, approximate time, event type, redacted summary, and fantasy theme. Original IDs, evidence, email bodies, exact amounts, order numbers, addresses, and local paths are never included in the request.

AkashML returns one of five allowlisted motif codes. The deterministic local renderer uses that code to shape chapter titles, recurring atmosphere, and a fictional embellishment while retaining local event anchors and order. If configuration is missing, the API fails, or the response does not contain exactly one allowed code, DayQuest safely uses the existing fully local generator. `Connected` is shown only after the selected motif influences the final story and local evaluation passes.

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
