"""Count per-character frequency from public WordPress sites (read-only REST GET).

usage: python tools/charfreq.py [--merge data/charfreq.json] https://news.example https://blog.example > out.json

Counts title, content and excerpt of posts and pages, plus names and descriptions of categories and tags.
Only the frequency order matters to the build; it decides which characters share the first slices.
"""
import argparse
import collections
import html
import json
import re
import sys
import urllib.request

TYPES = {"posts": "title,content,excerpt", "pages": "title,content,excerpt",
         "categories": "name,description", "tags": "name,description"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (charfreq)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r), int(r.headers.get("X-WP-TotalPages", "1"))


def text_of(item):
    strip = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s))
    parts = [strip(item[k]["rendered"]) for k in ("title", "content", "excerpt") if isinstance(item.get(k), dict)]
    parts += [item[k] for k in ("name", "description") if isinstance(item.get(k), str)]
    return "".join(parts)


def count_site(base):
    counts = collections.Counter()
    for kind, fields in TYPES.items():
        page, pages = 1, 1
        while page <= pages:
            items, pages = get(f"{base.rstrip('/')}/wp-json/wp/v2/{kind}?per_page=100&page={page}&_fields={fields}")
            for item in items:
                counts.update(text_of(item))
            print(f"{base} {kind} {page}/{pages}", file=sys.stderr, flush=True)
            page += 1
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sites", nargs="+")
    ap.add_argument("--merge", help="existing charfreq.json to add to")
    args = ap.parse_args()
    total = collections.Counter(json.load(open(args.merge, encoding="utf-8")) if args.merge else {})
    for site in args.sites:
        total.update(count_site(site))
    json.dump(dict(total), sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
