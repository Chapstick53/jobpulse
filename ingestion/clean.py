"""Data-cleaning pass: mark junk postings as excluded (reversible, non-destructive).

Raw data is never deleted — we set raw_postings.excluded=1 with a reason, so
extraction and rankings skip them but we can always revisit. Reasons:
  source_dropped  - RemoteOK (0% usable in validation sample, F9)
  non_english     - langdetect says not English (F12)
  too_short       - < MIN_WORDS words of real content (junk/gibberish, F13)
  duplicate       - near-identical to an earlier posting from same company (F10)

Usage: python -m ingestion.clean
"""
from difflib import SequenceMatcher

from langdetect import DetectorFactory, detect

from extraction.textclean import clean_text
from ingestion.db import connect

DetectorFactory.seed = 0  # deterministic langdetect
DROPPED_SOURCES = {"remoteok"}
MIN_WORDS = 40
# 0.92, not 0.85: big companies reuse the same boilerplate intro across DIFFERENT
# roles, which a loose threshold wrongly flags as duplicate (killed Lockheed/Wolt
# postings at 0.85). True re-posts (LawnStarter same job ×5 cities) are ~98%
# identical, so 0.92 still catches them. (DEVLOG F10 tuning.)
DUP_SIMILARITY = 0.92


def ensure_columns(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(raw_postings)")}
    if "excluded" not in cols:
        conn.execute("ALTER TABLE raw_postings ADD COLUMN excluded INTEGER DEFAULT 0")
    if "exclude_reason" not in cols:
        conn.execute("ALTER TABLE raw_postings ADD COLUMN exclude_reason TEXT")
    conn.commit()


def is_english(text: str) -> bool:
    try:
        return detect(text[:2000]) == "en"
    except Exception:
        return False


def norm(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalpha() or c.isspace())


def main():
    conn = connect()
    ensure_columns(conn)
    # reset so the pass is repeatable
    conn.execute("UPDATE raw_postings SET excluded=0, exclude_reason=NULL")
    conn.commit()

    rows = conn.execute(
        "SELECT id, source, company, title, description FROM raw_postings"
    ).fetchall()

    reasons = {}
    kept_sigs = {}  # company -> list of (id, normalized_text) already kept

    for pid, source, company, title, desc in rows:
        if source in DROPPED_SOURCES:
            reasons[pid] = "source_dropped"
            continue

        text = clean_text(desc)
        if len(text.split()) < MIN_WORDS:
            reasons[pid] = "too_short"
            continue
        if not is_english(text):
            reasons[pid] = "non_english"
            continue

        # dedup within same company against already-kept postings
        sig = norm(f"{title} {text}")[:1500]
        dup = False
        for kid, ktext in kept_sigs.get(company, []):
            if SequenceMatcher(None, sig, ktext).quick_ratio() >= DUP_SIMILARITY and \
               SequenceMatcher(None, sig, ktext).ratio() >= DUP_SIMILARITY:
                reasons[pid] = "duplicate"
                dup = True
                break
        if not dup:
            kept_sigs.setdefault(company, []).append((pid, sig))

    conn.executemany(
        "UPDATE raw_postings SET excluded=1, exclude_reason=? WHERE id=?",
        [(reason, pid) for pid, reason in reasons.items()],
    )
    # drop mentions for now-excluded postings so old rankings don't keep them
    conn.execute(
        "DELETE FROM mentions WHERE posting_id IN (SELECT id FROM raw_postings WHERE excluded=1)"
    )
    conn.commit()

    total = len(rows)
    excluded = len(reasons)
    print(f"Cleaning done. {total - excluded}/{total} kept, {excluded} excluded.\n")
    from collections import Counter
    for reason, n in Counter(reasons.values()).most_common():
        print(f"  {reason:16} {n}")
    kept_by_src = conn.execute(
        "SELECT source, SUM(excluded=0), COUNT(*) FROM raw_postings GROUP BY source"
    ).fetchall()
    print("\n  Kept by source:")
    for src, kept, tot in kept_by_src:
        print(f"    {src:12} {kept}/{tot}")


if __name__ == "__main__":
    main()
