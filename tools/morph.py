"""Morphological glyph edits for 昌明體 ChangMing Serif TC (base: Noto Serif TC).

opening(r): erode then dilate by r, rounds convex corners and blunts the triangular serifs.
closing(c): dilate then erode by c, rounds the inner corners of stroke turns.
thicken(d): net outward offset; thin horizontals gain proportionally more than verticals,
            which lowers stroke contrast. A lighter base weight keeps overall colour similar.
"""
import argparse
import json
import os
from multiprocessing import Pool

import pathops
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROUND = dict(cap=pathops.LineCap.ROUND_CAP, join=pathops.LineJoin.ROUND_JOIN, miter_limit=4)


def glyph_path(glyphset, name):
    path = pathops.Path()
    glyphset[name].draw(path.getPen(glyphSet=glyphset))
    path.simplify(fix_winding=True)
    return path


def stroke_of(path, radius):
    s = pathops.Path()
    s.addPath(path)
    s.stroke(radius * 2, **ROUND)
    # Round joins/caps come out as conics, which boolean ops reject.
    s.convertConicsToQuads()
    # A raw stroke outline self-overlaps heavily; resolving it first makes the following op far more stable.
    s.simplify(fix_winding=True)
    return s


def dilate(path, r):
    if r <= 0:
        return path
    return pathops.op(path, stroke_of(path, r), pathops.PathOp.UNION, fix_winding=True)


def erode(path, r):
    if r <= 0:
        return path
    return pathops.op(path, stroke_of(path, r), pathops.PathOp.DIFFERENCE, fix_winding=True)


def morph(path, opening=0.0, closing=0.0, thicken=0.0):
    if closing:
        path = erode(dilate(path, closing), closing)
    if opening:
        path = dilate(erode(path, opening), opening)
    if thicken > 0:
        path = dilate(path, thicken)
    elif thicken < 0:
        path = erode(path, -thicken)
    return path


def to_recording(path):
    path.convertConicsToQuads()
    rec = RecordingPen()
    path.draw(rec)
    return rec.value


# Worker state: one instanced font per process.
_WORK = {}


def _init(font_path, params):
    font = TTFont(font_path, lazy=True)
    _WORK["gs"] = font.getGlyphSet()
    _WORK["params"] = params


MAX_LOST = 0.04    # opening legitimately trims serif tips and hairline ends
MAX_EXCESS = 0.004  # ink far from any source stroke means a boolean op filled a counter (black blob)
GRID = 12


def lost_ink(src, out):
    """Share of the source area not covered by the result (via boolean op; fragile, used for diagnostics)."""
    if not src.area:
        return 0.0
    return abs(pathops.op(src, out, pathops.PathOp.DIFFERENCE, fix_winding=True).area) / abs(src.area)


def raster_check(src, out, reach):
    """Grid sampling with point containment only, independent of boolean ops.

    lost:   source samples not inside the result.
    excess: result samples outside the source with no source ink within `reach` units.
    """
    xmin, ymin, xmax, ymax = src.bounds
    pad = reach + GRID
    src_in = out_in = lost = excess = 0
    offsets = [(reach, 0), (-reach, 0), (0, reach), (0, -reach),
               (reach * 0.7, reach * 0.7), (-reach * 0.7, reach * 0.7), (reach * 0.7, -reach * 0.7), (-reach * 0.7, -reach * 0.7)]
    y = ymin - pad
    while y <= ymax + pad:
        x = xmin - pad
        while x <= xmax + pad:
            s, o = src.contains((x, y)), out.contains((x, y))
            if s:
                src_in += 1
                if not o:
                    lost += 1
            elif o:
                out_in += 1
                if not any(src.contains((x + dx, y + dy)) for dx, dy in offsets):
                    excess += 1
            x += GRID
        y += GRID
    if not src_in:
        return 0.0, 0.0
    return lost / src_in, excess / src_in


def scaled(path, k):
    p = pathops.Path()
    p.addPath(path)
    p.transform(k, 0, 0, k, 0, 0)
    return p


def _attempts(src, params):
    """Strategies in order of preference; skia ops are numerically fragile on some outlines."""
    yield "direct", lambda: morph(src, **params)
    yield "scaled4", lambda: scaled(morph(scaled(src, 4), **{k: v * 4 for k, v in params.items()}), 0.25)
    for j in (0.37, -0.41):
        yield f"jitter{j}", lambda j=j: morph(src, **{k: (v + j if v else v) for k, v in params.items()})
    if params.get("opening"):
        yield "no_opening", lambda: morph(src, **{**params, "opening": 0})
    if params.get("thicken"):
        yield "thicken_only", lambda: morph(src, thicken=params["thicken"])


def reach_for(params):
    """How far legitimate new ink may sit from the source outline."""
    return params.get("thicken", 0) + params.get("closing", 0) + 6


def _job(name):
    gs = _WORK["gs"]
    params = _WORK["params"]
    try:
        src = glyph_path(gs, name)
    except Exception as e:
        return name, ("error", f"source: {e}")
    if not list(src.segments):
        return name, None
    for label, attempt in _attempts(src, params):
        try:
            out = attempt()
            lost, excess = raster_check(src, out, reach_for(params))
            if lost > MAX_LOST or excess > MAX_EXCESS:
                continue
            if out.clockwise != src.clockwise:
                out.reverse()
            return name, (label, to_recording(out))
        except Exception:
            continue
    return name, ("error", "all strategies failed")


def rebuild(font_path, out_path, params, names=None, procs=None):
    """Apply morph to glyphs (all if names is None) of a static TTF and save."""
    font = TTFont(font_path)
    glyf = font["glyf"]
    order = names or [g for g in font.getGlyphOrder() if glyf[g].numberOfContours != 0]
    errors, strategies = [], {}
    with Pool(procs or os.cpu_count(), initializer=_init, initargs=(font_path, params)) as pool:
        for name, result in pool.imap_unordered(_job, order, chunksize=64):
            if result is None:
                continue
            label, rec = result
            if label == "error":
                errors.append((name, rec))  # glyph keeps its source outline
                continue
            strategies[label] = strategies.get(label, 0) + 1
            pen = TTGlyphPen(None)
            cu = Cu2QuPen(pen, max_err=1.0, reverse_direction=False)
            for op, args in rec:
                getattr(cu, op)(*args)
            old = glyf[name]
            old.recalcBounds(glyf)
            new = pen.glyph(dropImpliedOnCurves=True)
            new.recalcBounds(glyf)
            glyf[name] = new
            # The outline origin is placed at xMin - lsb, so a stale lsb shifts the whole glyph sideways.
            advance, _ = font["hmtx"][name]
            font["hmtx"][name] = (advance, new.xMin)
            if "vmtx" in font:
                vadvance, tsb = font["vmtx"][name]
                font["vmtx"][name] = (vadvance, tsb + (old.yMax - new.yMax))
    font.save(out_path)
    return {"glyphs": len(order), "strategies": strategies, "kept_source": len(errors), "kept_sample": errors[:10]}


def instance(src, weight, out_path):
    font = instancer.instantiateVariableFont(TTFont(src), {"wght": weight})
    font.save(out_path)
    return out_path


def measure(font_path):
    """Stroke thickness of a horizontal (一) and a vertical (丨) through their middles."""
    font = TTFont(font_path)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()

    def strip(char, horizontal):
        p = glyph_path(gs, cmap[ord(char)])
        xmin, ymin, xmax, ymax = p.bounds
        r = pathops.Path()
        if horizontal:  # vertical slice through x centre, measure height
            cx = (xmin + xmax) / 2
            r.moveTo(cx - 1, -1000); r.lineTo(cx + 1, -1000); r.lineTo(cx + 1, 2000); r.lineTo(cx - 1, 2000); r.close()
        else:
            cy = (ymin + ymax) / 2
            r.moveTo(-1000, cy - 1); r.lineTo(2000, cy - 1); r.lineTo(2000, cy + 1); r.lineTo(-1000, cy + 1); r.close()
        b = pathops.op(p, r, pathops.PathOp.INTERSECTION).bounds
        return round(b[3] - b[1]) if horizontal else round(b[2] - b[0])

    return {"horizontal_一": strip("一", True), "vertical_丨": strip("丨", False)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure"); m.add_argument("font")
    i = sub.add_parser("instance"); i.add_argument("src"); i.add_argument("weight", type=float); i.add_argument("out")
    r = sub.add_parser("rebuild"); r.add_argument("font"); r.add_argument("out"); r.add_argument("params")
    r.add_argument("--chars", default="")
    a = ap.parse_args()
    if a.cmd == "measure":
        print(json.dumps(measure(a.font), ensure_ascii=False))
    elif a.cmd == "instance":
        instance(a.src, a.weight, a.out)
    else:
        params = json.loads(a.params)
        names = None
        if a.chars:
            cmap = TTFont(a.font).getBestCmap()
            names = sorted({cmap[ord(c)] for c in a.chars if ord(c) in cmap})
        print(rebuild(a.font, a.out, params, names))
