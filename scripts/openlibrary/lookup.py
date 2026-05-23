"""Look up a book on Open Library and print its metadata as JSON.

Output fields: title, author, language, isbn, exact_title_match, author_match,
has_author, has_isbn, confidence, source.

Confidence tiers:
  high   - exact title match + has_author + (author matches if --author given) + has_isbn
  medium - same as high but missing ISBN
  low    - no exact title match, missing author, or author mismatch

Usage:
    .venv/bin/python scripts/openlibrary/lookup.py "Frog and Toad Are Friends" --language english
    .venv/bin/python scripts/openlibrary/lookup.py "Harry Potter" --language english --author "J.K. Rowling"
"""

import argparse
import json
import re
import sys
import requests

API_URL = "https://openlibrary.org/search.json"
EDITIONS_URL_FMT = "https://openlibrary.org{work_key}/editions.json"
TIMEOUT = 15

LANG_MAP = {"eng": "english", "spa": "spanish"}
LANG_REVERSE = {v: k for k, v in LANG_MAP.items()}


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", s or "")).strip().lower()


def language_contains(lang_codes: list | None, target: str) -> bool:
    if not lang_codes:
        return False
    target_code = LANG_REVERSE.get(target, target)
    return target_code in lang_codes


def map_language(lang_codes: list | None, prefer: str | None = None) -> str:
    """Return a human-readable language; if `prefer` is present in the list, report it."""
    if not lang_codes:
        return ""
    if prefer:
        prefer_code = LANG_REVERSE.get(prefer, prefer)
        if prefer_code in lang_codes:
            return prefer
    code = lang_codes[0]
    return LANG_MAP.get(code, code)


def author_tokens(name: str) -> set:
    return {t for t in re.split(r"[\s.]+", (name or "").lower()) if len(t) >= 3}


def surname(name: str) -> str:
    tokens = [t for t in re.split(r"[\s.]+", (name or "").lower()) if len(t) >= 3]
    return tokens[-1] if tokens else ""


def authors_match(query_author: str, doc_authors: list) -> bool:
    """Match on surname token — robust to 'J.K. Rowling' vs 'J. K. Rowling'."""
    q_surname = surname(query_author)
    if not q_surname:
        return False
    return any(q_surname in author_tokens(a) for a in doc_authors or [])


def pick_best(
    docs: list, query_title: str, query_author: str | None, query_language: str
) -> tuple[dict | None, dict]:
    q_title = normalize(query_title)

    exact_title_docs = [d for d in docs if normalize(d.get("title", "")) == q_title]
    lang_matched = [
        d for d in exact_title_docs if language_contains(d.get("language"), query_language)
    ]
    candidate_pool = lang_matched or exact_title_docs

    def score(d):
        has_author = bool(d.get("author_name"))
        has_isbn = bool(d.get("isbn"))
        author_ok = True
        if query_author and has_author:
            author_ok = authors_match(query_author, d["author_name"])
        return (has_author and author_ok, has_isbn, has_author)

    if candidate_pool:
        best = max(candidate_pool, key=score)
        exact_title_match = True
    elif docs:
        best = docs[0]
        exact_title_match = False
    else:
        return None, {}

    has_author = bool(best.get("author_name"))
    has_isbn = bool(best.get("isbn"))
    author_match = True
    if query_author:
        author_match = authors_match(query_author, best.get("author_name") or []) if has_author else False

    flags = {
        "exact_title_match": exact_title_match,
        "has_author": has_author,
        "has_isbn": has_isbn,
        "author_match": author_match,
    }
    return best, flags


def confidence_tier(flags: dict, author_supplied: bool) -> str:
    if not flags.get("exact_title_match"):
        return "low"
    if not flags.get("has_author"):
        return "low"
    if author_supplied and not flags.get("author_match"):
        return "low"
    if not flags.get("has_isbn"):
        return "medium"
    return "high"


def fetch_edition_isbn(work_key: str, target_language: str) -> str:
    """Fetch editions for a work and return one ISBN, preferring target language."""
    if not work_key:
        return ""
    target_code = LANG_REVERSE.get(target_language, target_language)
    try:
        resp = requests.get(
            EDITIONS_URL_FMT.format(work_key=work_key),
            params={"limit": 50},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return ""

    def pick_isbn(e):
        for k in ("isbn_13", "isbn_10"):
            if e.get(k):
                return e[k][0]
        return ""

    def is_target_lang(e):
        return any(
            l.get("key", "").endswith(f"/{target_code}")
            for l in (e.get("languages") or [])
        )

    fallback = ""
    for e in resp.json().get("entries") or []:
        isbn = pick_isbn(e)
        if not isbn:
            continue
        if is_target_lang(e):
            return isbn
        if not fallback:
            fallback = isbn
    return fallback


def search(title: str, author: str | None) -> list:
    params = {"title": title, "limit": 20}
    if author:
        params["author"] = author
    resp = requests.get(API_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("docs", []) or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("title", help="Book title to look up")
    ap.add_argument(
        "--language",
        choices=["english", "spanish"],
        required=True,
        help="Book's language (used to prefer the right edition)",
    )
    ap.add_argument("--author", default=None, help="Optional author name to narrow results")
    args = ap.parse_args()

    try:
        docs = search(args.title, args.author)
    except requests.RequestException as e:
        print(json.dumps({"error": "request_failed", "message": str(e)}), file=sys.stderr)
        sys.exit(1)

    best, flags = pick_best(docs, args.title, args.author, args.language)
    if not best:
        print(json.dumps({"error": "no_results", "query": args.title}))
        sys.exit(2)

    isbn = (best.get("isbn") or [""])[0]
    if not isbn:
        isbn = fetch_edition_isbn(best.get("key") or "", args.language)
    flags["has_isbn"] = bool(isbn)

    output = {
        "title": best.get("title") or "",
        "author": (best.get("author_name") or [""])[0],
        "language": map_language(best.get("language"), prefer=args.language),
        "isbn": isbn,
        **flags,
        "confidence": confidence_tier(flags, author_supplied=bool(args.author)),
        "source": "openlibrary.org",
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
