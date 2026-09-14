"""Add glyphs that Noto Serif TC lacks for Taiwanese Hokkien and Hakka, before morphing.

Layers, first match wins per code point; glyphs already in the base are never replaced:
  1. the base static instance (Noto Serif TC)
  2. Noto Serif CJK TC 2.003 static instance: identical outlines to Noto Serif TC for shared characters
  3. GenYo Min 2 TW (Source Han Serif V2 plus Taiwanese and Hakka additions, CFF)

usage: python tools/merge_supplement.py base.ttf out.ttf report.json layer2.ttf layer3.otf
"""
import json
import os
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

CHARSET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "taigi-hakka.json")


def wanted():
    data = json.load(open(CHARSET, encoding="utf-8"))
    return sorted({ord(c) for text in data.values() for c in text})


def copy_glyph(src, name, cff):
    """Outline of `name` in `src` as a decomposed TrueType glyph, plus the source yMax for vmtx."""
    gs = src.getGlyphSet()
    rec = DecomposingRecordingPen(gs)
    gs[name].draw(rec)
    bounds = BoundsPen(gs)
    gs[name].draw(bounds)
    pen = TTGlyphPen(None)
    # CFF outer contours run counter-clockwise; TrueType wants clockwise.
    target = Cu2QuPen(pen, max_err=1.0, reverse_direction=True) if cff else pen
    rec.replay(target)
    # Keep TrueType sources point-for-point identical, so morph sees exactly the outline Noto ships.
    return pen.glyph(dropImpliedOnCurves=cff), bounds.bounds


def add_glyph(font, cp, glyph, src, src_name, src_bounds):
    glyf = font["glyf"]
    name = f"u{cp:04X}" if cp > 0xFFFF else f"uni{cp:04X}"
    while name in glyf:
        name += ".sup"
    glyph.recalcBounds(glyf)
    order = font.getGlyphOrder() + [name]
    font.setGlyphOrder(order)
    glyf.glyphOrder = order
    glyf[name] = glyph
    advance, _ = src["hmtx"][src_name]
    empty = glyph.numberOfContours == 0
    font["hmtx"][name] = (advance, 0 if empty else glyph.xMin)
    if "vmtx" in font:
        if "vmtx" in src and src_bounds:
            vadvance, tsb = src["vmtx"][src_name]
            # tsb is measured from yMax; conversion may nudge yMax by a unit.
            font["vmtx"][name] = (vadvance, tsb + (src_bounds[3] - (0 if empty else glyph.yMax)))
        else:
            font["vmtx"][name] = (font["vhea"].advanceHeightMax, 0 if empty else font["OS/2"].sTypoAscender - glyph.yMax)
    for table in font["cmap"].tables:
        if not table.isUnicode():
            continue
        if table.format == 12 or (table.format == 4 and cp <= 0xFFFF):
            table.cmap[cp] = name
    return name


def main(base_path, out_path, report_path, *layers):
    font = TTFont(base_path, recalcTimestamp=False)
    upm = font["head"].unitsPerEm
    sources = []
    for path in layers:
        src = TTFont(path, lazy=True)
        assert src["head"].unitsPerEm == upm, f"{path}: unitsPerEm {src['head'].unitsPerEm} != {upm}"
        sources.append((path, src, src.getBestCmap(), "CFF " in src))
    base_cmap = font.getBestCmap()
    report = {"base": base_path, "layers": list(layers), "added": {}, "missing": []}
    for cp in wanted():
        if cp in base_cmap:
            continue
        for path, src, cmap, cff in sources:
            if cp in cmap:
                glyph, bounds = copy_glyph(src, cmap[cp], cff)
                add_glyph(font, cp, glyph, src, cmap[cp], bounds)
                report["added"][f"U+{cp:04X}"] = path.rsplit("/", 1)[-1]
                break
        else:
            report["missing"].append(f"U+{cp:04X} {chr(cp)}")
    font.save(out_path)
    by_layer = {}
    for layer in report["added"].values():
        by_layer[layer] = by_layer.get(layer, 0) + 1
    report["summary"] = {"added": len(report["added"]), "by_layer": by_layer, "missing": len(report["missing"])}
    json.dump(report, open(report_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:])
