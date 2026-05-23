"""Look up a book on hub.lexile.com and print its metadata as JSON.

Output fields: title, author, language, isbn, lexile, exact_title_match, source.
Lexile is a string like "400L" or "AD470L", or "" if not measurable.

Usage:
    .venv/bin/python scripts/lexile/lookup.py "Frog and Toad Are Friends"
    .venv/bin/python scripts/lexile/lookup.py "Caperucita Roja" --language spanish
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

CHROMIUM_PATH = "/usr/bin/google-chrome-stable"
RUNTIME_CONFIG = "runtime.yaml"
PAGE_URL = "https://hub.lexile.com/find-a-book/"
API_URL = "https://atlas-fab.lexile.com/free/search"


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", s or "")).strip().lower()


def format_lexile(measurements: dict, language: str) -> str:
    m = (measurements or {}).get(language) or {}
    if not m.get("measurable"):
        return ""
    code = m.get("lexile_code") or ""
    num = m.get("lexile")
    if num is None:
        return ""
    return f"{code}{num}L"


def pick_best(results: list, query: str) -> tuple[dict | None, bool]:
    q = normalize(query)
    for r in results:
        if normalize(r.get("title", "")) == q:
            return r, True
    return (results[0] if results else None), False


def chrome_path() -> str:
    config_path = Path(RUNTIME_CONFIG)
    if not config_path.exists():
        return CHROMIUM_PATH
    try:
        config = yaml.safe_load(config_path.read_text()) or {}
    except Exception:
        return CHROMIUM_PATH
    return (
        config.get("tools", {}).get("chrome_path")
        or CHROMIUM_PATH
    )


def search(query: str, language: str) -> dict | None:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome_path(), headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        page.goto(PAGE_URL, wait_until="load", timeout=30000)
        page.wait_for_timeout(1500)

        body = {
            "sort_by": "-score",
            "term": query,
            "page": 1,
            "results_per_page": 10,
            "spanish_br_range_search": False,
            "filters": {"language": language},
        }
        resp = page.request.post(
            API_URL,
            data=json.dumps(body),
            headers={
                "Content-Type": "application/json; version=1.0",
                "Accept": "application/json; version=1.0",
                "Origin": "https://hub.lexile.com",
                "Referer": "https://hub.lexile.com/",
            },
        )
        status = resp.status
        try:
            parsed = resp.json()
        except Exception:
            parsed = {"_raw": resp.text()}

        browser.close()
        return {"status": status, "parsed": parsed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("title", help="Book title to look up")
    ap.add_argument(
        "--language",
        choices=["english", "spanish"],
        default="english",
        help="Language to filter by (default: english)",
    )
    args = ap.parse_args()

    result = search(args.title, args.language)
    if not result or result["status"] != 200:
        print(json.dumps({"error": "search_failed", "raw": result}), file=sys.stderr)
        sys.exit(1)

    parsed = result["parsed"]
    if not parsed.get("success"):
        print(json.dumps({"error": "api_unsuccessful", "raw": parsed}), file=sys.stderr)
        sys.exit(1)

    results = parsed.get("data", {}).get("results", []) or []
    if not results:
        print(json.dumps({"error": "no_results", "query": args.title, "language": args.language}))
        sys.exit(2)

    best, exact = pick_best(results, args.title)
    if not best:
        print(json.dumps({"error": "no_results", "query": args.title}))
        sys.exit(2)

    language = best.get("language") or args.language
    output = {
        "title": best.get("title") or "",
        "author": (best.get("authors") or [""])[0],
        "language": language,
        "isbn": best.get("canonical_isbn") or "",
        "lexile": format_lexile(best.get("measurements") or {}, language),
        "exact_title_match": exact,
        "source": "hub.lexile.com",
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
