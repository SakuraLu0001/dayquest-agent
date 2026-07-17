# DayQuest

DayQuest is a privacy-first local agent that reconstructs a synthetic day from fragmented calendar, transaction, and email data, then turns the verified and redacted event skeleton into a deterministic fantasy adventure log.

> This MVP uses **synthetic demo data only**. Akash, Nexla, and Pomerium are placeholders and are not connected.

## Run locally

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

Click **Run DayQuest Agent** to view the reconstructed timeline, Privacy Gate, observation-driven loop trace, fantasy story cards, and stop reason.

## Verify

```powershell
python -m pytest -q
python -m compileall dayquest app.py
```

The agent reads only local files in `data/`. It makes no external API calls and uses no secrets. Missing or malformed sources are reported in the UI while successfully loaded sources remain available.
