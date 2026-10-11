#!/usr/bin/env python3
"""Cloudflare build: copy the site into dist/ and add the font CDN and download mirror.

Deployed as a Worker with static assets: production branch gh-pages, build
command "python3 cf-build.py", deploy command "npx wrangler deploy" (see
wrangler.jsonc). Release zips are fetched at build time instead of being
committed, and every one is checked against cf-sha256.txt. ZIP_DIR=<dir> takes
the zips from a local directory instead, for testing the build offline.

    /fonts/<version>/   web font kit of each version in cf-versions.txt
    /dl/v<latest>/      the four release zips of the latest version
    /fonts/latest/, /dl/latest/   302 to the latest version
"""
import hashlib
import io
import os
import shutil
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
RELEASE = "https://github.com/ivanusto/changming-serif-tc/releases/download/v%s/%s"
SKIP = {"dist", ".git", ".gitignore", "cf-build.py", "cf-versions.txt", "cf-sha256.txt",
        "wrangler.jsonc", ".wrangler"}


def versions():
    lines = open(os.path.join(HERE, "cf-versions.txt"), encoding="utf-8").read().splitlines()
    return [s.strip() for s in lines if s.strip() and not s.startswith("#")]


def known_sha():
    out = {}
    for line in open(os.path.join(HERE, "cf-sha256.txt"), encoding="utf-8"):
        if line.strip():
            sha, name = line.split()
            out[name] = sha
    return out


def fetch(version, name, sha, cache={}):
    if name in cache:
        return cache[name]
    if name not in sha:
        sys.exit("%s has no entry in cf-sha256.txt" % name)
    local = os.environ.get("ZIP_DIR")
    if local:
        blob = open(os.path.join(local, name), "rb").read()
    else:
        with urllib.request.urlopen(RELEASE % (version, name), timeout=600) as r:
            blob = r.read()
    got = hashlib.sha256(blob).hexdigest()
    if got != sha[name]:
        sys.exit("%s sha256 %s, expected %s" % (name, got, sha[name]))
    print("  %-40s %6.1f MB" % (name, len(blob) / 1048576), flush=True)
    cache[name] = blob
    return blob


def main():
    vers, sha = versions(), known_sha()
    latest = vers[-1]
    shutil.rmtree(DIST, ignore_errors=True)
    shutil.copytree(HERE, DIST, ignore=lambda d, names: SKIP & set(names) if d == HERE else set())

    for v in vers:
        kit = zipfile.ZipFile(io.BytesIO(fetch(v, "changming-serif-tc-%s-webfont.zip" % v, sha)))
        dest = os.path.join(DIST, "fonts", v)
        for item in kit.infolist():
            # The kit folder plus the licence, which has to travel with the fonts.
            if item.filename.startswith("changming/") and not item.is_dir():
                rel = item.filename[len("changming/"):]
            elif item.filename in ("OFL.txt", "README.txt"):
                rel = item.filename
            else:
                continue
            path = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(kit.read(item))

    dl = os.path.join(DIST, "dl", "v" + latest)
    os.makedirs(dl)
    for name in ("changming-serif-tc-%s-webfont.zip", "changming-webfont-%s.zip",
                 "changming-serif-tc-%s-ttf.zip", "changming-serif-tc-%s-woff2.zip"):
        name %= latest
        with open(os.path.join(dl, name), "wb") as f:
            f.write(fetch(latest, name, sha))

    with open(os.path.join(DIST, "_redirects"), "w") as f:
        f.write("/fonts/latest/* /fonts/%s/:splat 302\n" % latest)
        f.write("/dl/latest/* /dl/v%s/:splat 302\n" % latest)
    print("built dist/ with fonts %s, downloads v%s" % (", ".join(vers), latest))


if __name__ == "__main__":
    main()
