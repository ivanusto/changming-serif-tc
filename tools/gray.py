"""Gray (ink share of the em square) report for the most frequent hanzi, source against morph.

usage: python tools/gray.py work/base-300.ttf work/morph-400.ttf [extra fonts...]
Prints median, p95, interquartile range of gray relative to the median, the darkest glyphs,
and probe characters, so changes to the morph can be compared on evenness of colour.
"""
import json
import os
import sys

from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(__file__))
from morph import glyph_path  # noqa: E402

TOP = 3000
PROBE = "鷹驪豔鸚鬱靈籲讓書國日一"


def frequent_hanzi():
    freq = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "charfreq.json")))
    ranked = sorted(freq.items(), key=lambda kv: -kv[1])
    return [c for c, _ in ranked if "一" <= c <= "鿿"][:TOP]


def grays(font_path, chars):
    font = TTFont(font_path)
    gs, cmap, em2 = font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm ** 2
    return {c: abs(glyph_path(gs, cmap[ord(c)]).area) / em2 for c in chars if ord(c) in cmap}


def report(font_path, chars):
    g = grays(font_path, chars)
    top = [c for c in chars[:TOP] if c in g]
    ranked = sorted(g[c] for c in top)
    q = lambda f: ranked[int(f * (len(ranked) - 1))]
    med = q(0.5)
    return {
        "font": os.path.basename(font_path),
        "median": round(med, 4),
        "p95": round(q(0.95), 4),
        "iqr_rel": round((q(0.75) - q(0.25)) / med, 4),
        "p95_rel": round(q(0.95) / med, 3),
        "darkest": " ".join(sorted(top, key=lambda c: -g[c])[:15]),
        "probe_rel": {c: round(g[c] / med, 3) for c in PROBE if c in g},
    }


if __name__ == "__main__":
    chars = list(dict.fromkeys(frequent_hanzi() + list(PROBE)))
    for path in sys.argv[1:]:
        print(json.dumps(report(path, chars), ensure_ascii=False))
