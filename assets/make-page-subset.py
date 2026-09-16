#!/usr/bin/env python3
"""Build a page specific subset of ChangMing Serif TC for this demo site.

The sliced web font kit in assets/changming/ downloads whole 100 KB slices for a
single rare character, and this page uses a fair number of them (灩 霰 齌 隳 ...).
A subset holding exactly the characters the page renders is declared after the
kit CSS, so it wins for those code points; anything a visitor types into the
type tester still falls through to the kit slices.

Needs the built full weights from the font repo:
    python3 make-page-subset.py ~/changming-serif-tc/build/fonts
Writes assets/changming-page/cmsr-page-{400,700}.woff2 and prints the CSS.
"""
import hashlib
import html as htmllib
import os
import re
import sys

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
OUT = os.path.join(HERE, "changming-page")

# Whole printable ASCII, not just the characters the markup happens to use. One
# code point left out, the space in particular, is enough to pull the kit 60 KB
# latin slice, which costs more than carrying the missing glyphs here.
EXTRA = "".join(chr(c) for c in range(0x20, 0x7F))


def page_chars(*paths):
    chars = set(EXTRA)
    for path in paths:
        raw = open(path, encoding="utf-8").read()
        body = raw[raw.index("<body"):] if "<body" in raw else raw
        body = re.sub(r"<style[\s\S]*?</style>", " ", body)
        body = re.sub(r"<script[\s\S]*?</script>", " ", body)
        body = re.sub(r"<[^>]+>", " ", body)
        chars |= set(htmllib.unescape(body))
    return {c for c in chars if c in " 　" or not c.isspace()}


def build(src_dir, chars):
    os.makedirs(OUT, exist_ok=True)
    css = []
    for weight, stem in ((400, "Regular"), (700, "Bold")):
        font = TTFont(os.path.join(src_dir, "ChangMingSerifTC-%s.ttf" % stem),
                      recalcTimestamp=False)
        have = {c for c in chars if ord(c) in font.getBestCmap()}
        missing = sorted(chars - have)
        if missing:
            print("  not in the font, left to fallback: %s" % "".join(missing))

        # Same knobs as tools/build.py subset_woff2 in the font repo, so a page
        # glyph is byte for byte what the shipped slices would have given.
        options = Options()
        options.flavor = "woff2"
        options.hinting = False
        options.desubroutinize = True
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.name_languages = ["*"]
        options.notdef_outline = True
        options.glyph_names = False
        subsetter = Subsetter(options=options)
        subsetter.populate(unicodes=[ord(c) for c in have])
        subsetter.subset(font)

        # Subsetter does not apply options.flavor; without this the file is a
        # plain TTF with a .woff2 name and is roughly four times the size.
        font.flavor = "woff2"
        tmp = os.path.join(OUT, "tmp.woff2")
        font.save(tmp)
        blob = open(tmp, "rb").read()
        os.remove(tmp)
        digest = hashlib.sha256(blob).hexdigest()[:8]
        name = "cmsr-page-%d.%s.woff2" % (weight, digest)
        for old in os.listdir(OUT):
            if old.startswith("cmsr-page-%d." % weight):
                os.remove(os.path.join(OUT, old))
        open(os.path.join(OUT, name), "wb").write(blob)

        # The range has to match the shipped glyphs exactly. A code point listed
        # here but absent from the file would fall past the whole family instead
        # of down to the next slice.
        cmap = set(TTFont(os.path.join(OUT, name)).getBestCmap())
        css.append(
            '@font-face{font-family:"ChangMing Serif TC";font-style:normal;'
            "font-weight:%d;font-display:swap;"
            'src:url(changming-page/%s) format("woff2");unicode-range:%s}'
            % (weight, name, ranges(sorted(cmap)))
        )
        print("  %-34s %6.1f KB  %d glyphs" % (name, len(blob) / 1024, len(cmap)))
    return "\n".join(css)


def ranges(cps):
    out, start, prev = [], cps[0], cps[0]
    for cp in cps[1:] + [None]:
        if cp == prev + 1:
            prev = cp
            continue
        out.append("U+%X" % start if start == prev else "U+%X-%X" % (start, prev))
        if cp is None:
            break
        start = prev = cp
    return ",".join(out)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
        "~/changming-serif-tc/build/fonts")
    sources = [os.path.join(SITE, "index.html"), os.path.join(HERE, "og-card.html")]
    sources += sys.argv[2:]
    chars = page_chars(*sources)
    print("%d distinct characters on the page" % len(chars))
    css = build(src, chars)
    open(os.path.join(HERE, "changming-page.css"), "w", encoding="utf-8").write(css + "\n")
    print("\nwrote assets/changming-page.css")
