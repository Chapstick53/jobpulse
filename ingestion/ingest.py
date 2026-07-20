"""Run all sources and store new postings. Usage: python -m ingestion.ingest"""
from ingestion import db
from ingestion.sources import adzuna, arbeitnow, remoteok, remotive

SOURCES = {
    "remotive": remotive,
    "remoteok": remoteok,
    "arbeitnow": arbeitnow,
    "adzuna": adzuna,
}


def main() -> None:
    conn = db.connect()
    total_new = 0
    for name, module in SOURCES.items():
        print(f"[{name}] fetching...")
        try:
            postings = module.fetch()
        except Exception as e:  # one broken source must not kill the weekly run
            print(f"  ERROR: {e}")
            continue
        new = db.insert_postings(conn, name, postings)
        total_new += new
        print(f"  fetched {len(postings)}, new {new}")

    count = conn.execute("SELECT COUNT(*) FROM raw_postings").fetchone()[0]
    print(f"\nDone. {total_new} new postings this run. Total in DB: {count}")


if __name__ == "__main__":
    main()
