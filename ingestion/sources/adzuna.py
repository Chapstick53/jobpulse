"""Adzuna — free developer tier, needs APP_ID + APP_KEY from https://developer.adzuna.com.

Multi-country aggregator: one API, ~20 countries. Set the env vars
ADZUNA_APP_ID and ADZUNA_APP_KEY (locally in a .env / shell, on GitHub via
repo Secrets) and this source activates automatically; without them it is
skipped so the pipeline still runs.
"""
import os

import httpx

COUNTRIES = ["us", "gb", "in", "de", "ca", "au"]  # widen anytime
PAGES_PER_COUNTRY = 5  # 50 results per page
BASE = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


def fetch() -> list[dict]:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("  (adzuna skipped — set ADZUNA_APP_ID / ADZUNA_APP_KEY to enable)")
        return []

    out = []
    for country in COUNTRIES:
        for page in range(1, PAGES_PER_COUNTRY + 1):
            resp = httpx.get(
                BASE.format(country=country, page=page),
                params={
                    "app_id": app_id,
                    "app_key": app_key,
                    "results_per_page": 50,
                    "category": "it-jobs",
                    "content-type": "application/json",
                },
                timeout=60,
            )
            resp.raise_for_status()
            for job in resp.json().get("results", []):
                out.append(
                    {
                        "source_id": job["id"],
                        "title": job.get("title"),
                        "company": (job.get("company") or {}).get("display_name"),
                        "location": (job.get("location") or {}).get("display_name"),
                        "remote": 0,
                        "description": job.get("description"),
                        "url": job.get("redirect_url"),
                        "salary_text": _salary(job),
                        "posted_at": job.get("created"),
                        "raw": {**job, "_country": country},
                    }
                )
    return out


def _salary(job: dict) -> str | None:
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if lo or hi:
        return f"{lo or '?'}-{hi or '?'}"
    return None
