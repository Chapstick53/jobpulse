"""Remotive — free API, no key needed. Remote jobs worldwide."""
import httpx

API_URL = "https://remotive.com/api/remote-jobs"


def fetch() -> list[dict]:
    resp = httpx.get(API_URL, timeout=60)
    resp.raise_for_status()
    jobs = resp.json().get("jobs", [])
    return [
        {
            "source_id": job["id"],
            "title": job.get("title"),
            "company": job.get("company_name"),
            "location": job.get("candidate_required_location"),
            "remote": 1,
            "description": job.get("description"),
            "url": job.get("url"),
            "salary_text": job.get("salary") or None,
            "posted_at": job.get("publication_date"),
            "raw": job,
        }
        for job in jobs
    ]
