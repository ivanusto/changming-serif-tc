"""Compare a morphed font against its source: flag glyphs whose contours or ink area dropped."""
import json
import sys

import pathops
from fontTools.ttLib import TTFont

sys.path.insert(0, __import__("os").path.dirname(__file__))
from morph import glyph_path, raster_check  # noqa: E402


def main(src_path, out_path, report_path, reach):
    REACH = float(reach)
    src, out = TTFont(src_path), TTFont(out_path)
    sgs, ogs = src.getGlyphSet(), out.getGlyphSet()
    cmap = {v: k for k, v in src.getBestCmap().items()}
    flagged = []
    for name in src.getGlyphOrder():
        if src["glyf"][name].numberOfContours == 0:
            continue
        sp, op = glyph_path(sgs, name), glyph_path(ogs, name)
        lost, excess = raster_check(sp, op, REACH)
        if lost > 0.04 or excess > 0.004:
            cp = cmap.get(name)
            flagged.append({"glyph": name, "char": chr(cp) if cp else "", "lost": round(lost, 3), "excess": round(excess, 4)})
    flagged.sort(key=lambda f: -(f["lost"] + f["excess"] * 10))
    json.dump(flagged, open(report_path, "w"), ensure_ascii=False, indent=0)
    cjk = [f for f in flagged if f["char"] and ("㐀" <= f["char"] <= "鿿")]
    print(json.dumps({"flagged": len(flagged), "cjk_flagged": len(cjk), "worst": flagged[:12]}, ensure_ascii=False))
    if flagged:
        sys.exit(1)  # stop the build: some outlines lost ink or gained a blob


if __name__ == "__main__":
    main(*sys.argv[1:5])
