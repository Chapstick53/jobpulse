"""Arbeitnow — free API, no key needed. Mostly Europe; adds non-remote postings."""
import httpx

API_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 10


def fetch() -> list[dict]:
    out = []
    url = API_URL
    for _ in range(MAX_PAGES):
        resp = httpx.get(url, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        for job in payload.get("data", []):
            out.append(
                {
                    "source_id": job["slug"],
                    "title": job.get("title"),
                    "company": job.get("company_name"),
                    "location": job.get("location"),
                    "remote": 1 if job.get("remote") else 0,
                    "description": job.get("description"),
                    "url": job.get("url"),
                    "salary_text": None,
                    "posted_at": _epoch_to_iso(job.get("created_at")),
                    "raw": job,
                }
            )
        url = (payload.get("links") or {}).get("next")
        if not url:
            break
    return out


def _epoch_to_iso(ts) -> str | None:
    from datetime import datetime, timezone

    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
