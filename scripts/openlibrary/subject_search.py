"""Discover books on a topic via Open Library and classify them by reading level.

Returns a JSON object with a `results` list. Each result includes:
  title, author, isbn, first_publish_year, pages, type, first_sentence,
  work_key, url, source

Type values (for bucketing in calling skills):
  picture_book   — typically <= 64 pages or tagged as picture book
  chapter_book   — juvenile-tagged, <= 250 pages
  middle_grade   — juvenile-tagged, > 250 pages
  young_adult    — tagged as young adult / YA
  adult          — everything else; suitable for read-aloud

Usage:
    .venv/bin/python scripts/openlibrary/subject_search.py "ancient Maya jade"
    .venv/bin/python scripts/openlibrary/subject_search.py "Maya civilization" --limit 10
"""

import argparse
import json
import sys
import requests

API_URL = "https://openlibrary.org/search.json"
TIMEOUT = 15

FIELDS = ",".join([
    "key", "title", "author_name", "isbn", "first_publish_year",
    "subject", "first_sentence", "number_of_pages_median",
])


def classify_book(doc: dict) -> str:
    pages = doc.get("number_of_pages_median") or 0
    subjects = " ".join(s.lower() for s in (doc.get("subject") or []))

    if "picture book" in subjects or (0 < pages <= 64):
        return "picture_book"
    if "young adult" in subjects or "ya fiction" in subjects:
        return "young_adult"
    if any(t in subjects for t in ("juvenile fiction", "juvenile literature", "children's stories", "children")):
        return "chapter_book" if pages <= 250 else "middle_grade"
    if 0 < pages <= 250:
        return "chapter_book"
    return "adult"


def search(query: str, limit: int, extra_params: dict | None = None) -> list:
    params = {"q": query, "limit": limit, "fields": FIELDS, **(extra_params or {})}
    resp = requests.get(API_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("docs", []) or []


def discover(query: str, limit: int) -> list:
    """Two-pass search: juvenile-filtered first, then broad. Deduplicates by work key."""
    seen: set = set()
    results = []

    for extra in ({"subject": "juvenile literature"}, {}):
        try:
            docs = search(query, limit, extra)
        except requests.RequestException:
            continue
        for doc in docs:
            key = doc.get("key", "")
            if key and key not in seen:
                seen.add(key)
                results.append(doc)

    return results


def format_result(doc: dict) -> dict:
    isbn = (doc.get("isbn") or [""])[0]
    first_sentence = doc.get("first_sentence") or ""
    if isinstance(first_sentence, list):
        first_sentence = first_sentence[0] if first_sentence else ""
    if isinstance(first_sentence, dict):
        first_sentence = first_sentence.get("value", "")
    key = doc.get("key") or ""
    url = f"https://openlibrary.org{key}" if key else ""
    return {
        "title": doc.get("title") or "",
        "author": (doc.get("author_name") or [""])[0],
        "isbn": isbn,
        "first_publish_year": doc.get("first_publish_year"),
        "pages": doc.get("number_of_pages_median"),
        "type": classify_book(doc),
        "first_sentence": first_sentence[:200] if first_sentence else "",
        "work_key": key,
        "url": url,
        "source": "openlibrary.org",
    }


def main():
    ap = argparse.ArgumentParser(description="Discover books on a topic via Open Library.")
    ap.add_argument("query", help="Topic or subject to search for")
    ap.add_argument("--limit", type=int, default=15, help="Max results to return (default: 15)")
    args = ap.parse_args()

    try:
        docs = discover(args.query, args.limit)
    except requests.RequestException as e:
        print(json.dumps({"error": "request_failed", "message": str(e)}), file=sys.stderr)
        sys.exit(1)

    if not docs:
        print(json.dumps({"error": "no_results", "query": args.query}))
        sys.exit(2)

    output = {
        "query": args.query,
        "results": [format_result(d) for d in docs[:args.limit]],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
