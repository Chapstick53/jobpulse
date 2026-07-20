"""Build monthly rankings from extracted mentions.

Writes the `rankings` table: for each month + category, how many postings
mention each skill, ranked. The dashboard just reads this table.
Usage: python -m aggregation.aggregate
"""
from ingestion.db import connect

RANKINGS_SCHEMA = """
DROP TABLE IF EXISTS rankings;
CREATE TABLE rankings (
    month         TEXT NOT NULL,      -- e.g. '2026-07'
    category      TEXT NOT NULL,
    skill         TEXT NOT NULL,
    postings      INTEGER NOT NULL,   -- postings that month mentioning the skill
    rank          INTEGER NOT NULL
);
"""

# A posting belongs to the month it was posted; if the source didn't tell us,
# fall back to when we ingested it.
RANKINGS_QUERY = """
INSERT INTO rankings (month, category, skill, postings, rank)
SELECT month, category, skill, postings,
       RANK() OVER (PARTITION BY month, category ORDER BY postings DESC)
FROM (
    SELECT substr(COALESCE(p.posted_at, p.ingested_at), 1, 7) AS month,
           m.category, m.skill, COUNT(DISTINCT m.posting_id) AS postings
    FROM mentions m
    JOIN raw_postings p ON p.id = m.posting_id
    WHERE m.skill != '__none__'
    GROUP BY month, m.category, m.skill
);
"""


def main() -> None:
    conn = connect()
    conn.executescript(RANKINGS_SCHEMA)
    conn.execute(RANKINGS_QUERY)
    conn.commit()

    latest = conn.execute("SELECT MAX(month) FROM rankings").fetchone()[0]
    print(f"Rankings rebuilt. Latest month: {latest}\n")
    for category, title in [
        ("technology", "TOP TECHNOLOGIES"),
        ("programming_language", "TOP PROGRAMMING LANGUAGES"),
        ("soft_skill", "TOP SOFT SKILLS"),
    ]:
        rows = conn.execute(
            """SELECT skill, postings FROM rankings
               WHERE month = ? AND category = ? ORDER BY rank LIMIT 10""",
            (latest, category),
        ).fetchall()
        print(f"--- {title} ({latest}) ---")
        for i, (skill, n) in enumerate(rows, 1):
            print(f"{i:2}. {skill:<22} {n} postings")
        print()


if __name__ == "__main__":
    main()
