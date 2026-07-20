"""Path A extraction: spaCy EntityRuler with curated skill lists.

Reads raw_postings, finds skill/technology/soft-skill mentions, writes them
to the `mentions` table. Only processes postings not extracted yet, so the
weekly run stays fast. Usage: python -m extraction.extract
"""
import html
import json
import re
import sqlite3
from pathlib import Path

import spacy

from ingestion.db import connect

RULES_PATH = Path(__file__).resolve().parent / "rules" / "skills.json"
EXTRACTOR_VERSION = "rules-v1"

MENTIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS mentions (
    posting_id        INTEGER NOT NULL REFERENCES raw_postings(id),
    category          TEXT NOT NULL,     -- programming_language | technology | soft_skill
    skill             TEXT NOT NULL,     -- canonical name, e.g. "JavaScript"
    extractor_version TEXT NOT NULL,
    UNIQUE (posting_id, category, skill, extractor_version)
);
CREATE INDEX IF NOT EXISTS idx_mentions_skill ON mentions (category, skill);
"""

TAG_RE = re.compile(r"<[^>]+>")

CATEGORY_LABELS = {
    "programming_languages": "programming_language",
    "ambiguous_case_sensitive": "programming_language",
    "technologies": "technology",
    "soft_skills": "soft_skill",
}


def strip_html(text: str) -> str:
    return html.unescape(TAG_RE.sub(" ", text or ""))


def build_nlp() -> spacy.language.Language:
    """A blank English pipeline + two EntityRulers built from skills.json.

    Ruler 1 matches case-insensitively (LOWER). Ruler 2 is case-sensitive,
    for names like "Go", "R", "C" that are ordinary words/letters otherwise.
    """
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    nlp = spacy.blank("en")

    ruler_ci = nlp.add_pipe(
        "entity_ruler", name="ruler_ci", config={"phrase_matcher_attr": "LOWER"}
    )
    ruler_cs = nlp.add_pipe("entity_ruler", name="ruler_cs")

    patterns_ci, patterns_cs = [], []
    for section, entries in rules.items():
        if section.startswith("_"):
            continue
        label = CATEGORY_LABELS[section]
        target = patterns_cs if section == "ambiguous_case_sensitive" else patterns_ci
        for canonical, aliases in entries.items():
            for alias in aliases:
                target.append(
                    {"label": label, "pattern": alias, "id": f"{label}::{canonical}"}
                )
    ruler_ci.add_patterns(patterns_ci)
    ruler_cs.add_patterns(patterns_cs)
    return nlp


def main() -> None:
    conn = connect()
    conn.executescript(MENTIONS_SCHEMA)

    todo = conn.execute(
        """SELECT id, title, description FROM raw_postings
           WHERE id NOT IN (
               SELECT DISTINCT posting_id FROM mentions WHERE extractor_version = ?
           )""",
        (EXTRACTOR_VERSION,),
    ).fetchall()
    print(f"{len(todo)} postings to extract")
    if not todo:
        return

    nlp = build_nlp()
    rows = []
    texts = (
        (pid, strip_html(f"{title or ''}. {desc or ''}")[:20000])
        for pid, title, desc in todo
    )
    for pid, text in texts:
        found = set()
        for ent in nlp(text).ents:
            label, canonical = ent.ent_id_.split("::", 1)
            found.add((label, canonical))
        # A posting with zero matches still gets a marker row so we don't
        # re-process it every run.
        if not found:
            found.add(("none", "__none__"))
        rows.extend((pid, cat, skill, EXTRACTOR_VERSION) for cat, skill in found)

    conn.executemany(
        "INSERT OR IGNORE INTO mentions (posting_id, category, skill, extractor_version) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    n = conn.execute(
        "SELECT COUNT(*) FROM mentions WHERE skill != '__none__'"
    ).fetchone()[0]
    print(f"Done. {n} skill mentions in DB.")


if __name__ == "__main__":
    main()
