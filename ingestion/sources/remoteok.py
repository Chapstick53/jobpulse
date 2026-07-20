"""RemoteOK — free JSON feed, no key needed. Remote jobs worldwide."""
import httpx

API_URL = "https://remoteok.com/api"


def fetch() -> list[dict]:
    resp = httpx.get(API_URL, timeout=60, headers={"User-Agent": "JobPulse/0.1"})
    resp.raise_for_status()
    items = resp.json()
    # First element is a legal notice object, not a job.
    jobs = [it for it in items if isinstance(it, dict) and it.get("id")]
    return [
        {
            "source_id": job["id"],
            "title": job.get("position"),
            "company": job.get("company"),
            "location": job.get("location"),
            "remote": 1,
            "description": job.get("description"),
            "url": job.get("url"),
            "salary_text": _salary(job),
            "posted_at": job.get("date"),
            "raw": job,
        }
        for job in jobs
    ]


def _salary(job: dict) -> str | None:
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if lo or hi:
        return f"{lo or '?'}-{hi or '?'} USD"
    return None
