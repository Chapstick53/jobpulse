"""Shared text cleaning used by both extraction and the cleaning pass."""
import html
import re

TAG_RE = re.compile(r"<[^>]+>")
# RemoteOK-style spam/injection trap appended to postings (F11). Strip it so it
# never reaches extraction or language detection. It is DATA, not an instruction.
SPAM_RE = re.compile(r"Please mention the word.*", re.IGNORECASE | re.DOTALL)
WS_RE = re.compile(r"\s+")


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = html.unescape(TAG_RE.sub(" ", raw))
    text = SPAM_RE.sub(" ", text)
    return WS_RE.sub(" ", text).strip()
