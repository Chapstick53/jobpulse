# JobPulse

Job-market trend intelligence: live postings from multiple free job APIs → skill extraction → monthly rankings of in-demand technologies, languages, and soft skills.

**Status:** data pipeline live (ingestion → extraction → rankings). Dashboard coming next.

## Pipeline

```
free job APIs (Remotive, RemoteOK, Arbeitnow, Adzuna)
  → ingestion/   SQLite raw_postings (append-only, deduped)
  → extraction/  spaCy EntityRuler finds skill/tech/soft-skill mentions
  → aggregation/ monthly rankings table
  → app/         Streamlit dashboard (soon)
```

Runs weekly via GitHub Actions (`.github/workflows/ingest.yml`), which commits the updated `data/jobpulse.db`.

## Run locally

```
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m ingestion.ingest
.venv/Scripts/python -m extraction.extract
.venv/Scripts/python -m aggregation.aggregate
```

Optional: create a free account at https://developer.adzuna.com and set `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` to enable the multi-country Adzuna source.

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the full roadmap.
