"""Build 昌明體 ChangMing Serif TC: frequency-ordered unicode-range slices plus the WordPress plugin zip.

Inputs:  work/morph-400.ttf, work/morph-700.ttf (made by tools/morph.py via build.sh)
         data/charfreq.json (per-character counts, made by tools/charfreq.py)
Output:  build/changming-webfont/ (plugin tree), build/changming-webfont-<version>.zip, build/build-report.md
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import zipfile

import brotli
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
WEIGHTS = {400: "Regular", 700: "Bold"}

CFG = {
    "family": "ChangMing Serif TC",
    "local_family": "昌明體",
    "ps_family": "ChangMingSerifTC",
    "slug": "changming-webfont",
    "prefix": "cmsr",
    "static_src": {400: os.path.join(ROOT, "work", "morph-400.ttf"),
                   700: os.path.join(ROOT, "work", "morph-700.ttf")},
    "ofl": os.path.join(ROOT, "fonts", "OFL.txt"),
    "plugin": os.path.join(ROOT, "plugin"),
    "php": "changming-webfont.php",
    "extra_files": ["includes", "uninstall.php"],
    "charfreq": os.path.join(ROOT, "data", "charfreq.json"),
    "description": "subset and morph of Noto Serif TC",
}

HOT_SIZE = 500     # most frequent characters, preloaded together with Latin
FREQ_SLICE = 150   # remaining characters seen in the corpus, by frequency
TAIL_SLICE = 200   # everything else in the font; small so a rare character costs little

CONTENT_RANGES = [(0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF)]
# CJK symbols, fullwidth ASCII forms and fullwidth signs (not halfwidth kana/hangul).
PUNCT_RANGES = [(0x3000, 0x303F), (0xFF01, 0xFF60), (0xFFE0, 0xFFE6)]
# Latin: ASCII, Latin-1 and general punctuation.
LATIN_RANGES = [(0x0020, 0x007E), (0x00A0, 0x00FF), (0x2000, 0x206F)]
# Everything else CJK-ish that the font carries goes to the tail so it still renders.
TAIL_RANGES = CONTENT_RANGES + [
    (0x2E80, 0x2FDF), (0x3100, 0x312F), (0x3190, 0x31BF), (0x3200, 0x33FF),
    (0xFE10, 0xFE1F), (0xFE30, 0xFE4F), (0x20000, 0x2FFFF),
]


def in_ranges(cp, ranges):
    return any(a <= cp <= b for a, b in ranges)


def big5_level1():
    """Big5 level-1 common characters (0xA440 to 0xC67E), a stand-in for the MoE common character list."""
    out = []
    for hi in range(0xA4, 0xC7):
        for lo in list(range(0x40, 0x7F)) + list(range(0xA1, 0xFF)):
            if (hi, lo) > (0xC6, 0x7E):
                return out
            try:
                out.append(ord(bytes([hi, lo]).decode("big5")))
            except UnicodeDecodeError:
                pass
    return out


def chunks(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def plan_slices(cmap):
    counts = json.load(open(CFG["charfreq"], encoding="utf-8"))
    content = sorted(
        (ord(c) for c in counts if len(c) == 1 and in_ranges(ord(c), CONTENT_RANGES) and ord(c) in cmap),
        key=lambda cp: (-counts[chr(cp)], cp),
    )
    punct = sorted(cp for cp in cmap if in_ranges(cp, PUNCT_RANGES))
    slices = [("l0", sorted(cp for cp in cmap if in_ranges(cp, LATIN_RANGES))),
              ("h0", sorted(content[:HOT_SIZE] + punct))]
    for i, part in enumerate(chunks(content[HOT_SIZE:], FREQ_SLICE), 1):
        slices.append((f"f{i:02d}", sorted(part)))
    used = set(content) | set(punct)
    big5 = sorted({cp for cp in big5_level1() if cp in cmap and cp not in used})
    for i, part in enumerate(chunks(big5, TAIL_SLICE), 1):
        slices.append((f"b{i:02d}", part))
    used |= set(big5)
    rest = sorted(cp for cp in cmap if in_ranges(cp, TAIL_RANGES) and cp not in used)
    for i, part in enumerate(chunks(rest, TAIL_SLICE), 1):
        slices.append((f"u{i:02d}", part))
    return slices


def unicode_range(cps):
    runs, start, prev = [], None, None
    for cp in cps:
        if start is None:
            start = prev = cp
        elif cp == prev + 1:
            prev = cp
        else:
            runs.append((start, prev))
            start = prev = cp
    if start is not None:
        runs.append((start, prev))
    return ",".join(f"U+{a:X}" if a == b else f"U+{a:X}-{b:X}" for a, b in runs)


def rename(font, weight):
    style = WEIGHTS[weight]
    name = font["name"]
    keep = {0, 7, 8, 9, 11, 12, 13, 14}
    name.names = [n for n in name.names if n.nameID in keep]
    ps = f"{CFG['ps_family']}-{style}"
    for nid, value in {
        1: CFG["family"], 2: style, 3: f"{ps};{CFG['description'].replace(' ', '-')}", 4: f"{CFG['family']} {style}",
        5: f"Version 1.0; {CFG['description']}", 6: ps,
    }.items():
        name.setName(value, nid, 3, 1, 0x409)
    # Traditional Chinese (Taiwan) family and full names.
    name.setName(CFG["local_family"], 1, 3, 1, 0x404)
    name.setName(f"{CFG['local_family']} {style}", 4, 3, 1, 0x404)
    font["OS/2"].usWeightClass = weight
    font["OS/2"].fsSelection = (font["OS/2"].fsSelection & ~0b1100001) | (0b100000 if weight == 700 else 0b1000000)
    font["head"].macStyle = 1 if weight == 700 else 0


def subset_woff2(src_path, cps):
    font = TTFont(src_path, recalcTimestamp=False)
    opts = Options()
    opts.flavor = "woff2"
    opts.hinting = False
    opts.desubroutinize = True
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]  # keep the zh-TW names
    opts.notdef_outline = True
    opts.glyph_names = False
    sub = Subsetter(opts)
    sub.populate(unicodes=cps)
    sub.subset(font)
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    args = ap.parse_args()

    os.makedirs(BUILD, exist_ok=True)
    tmp = os.path.join(BUILD, "tmp")
    plugin_dir = os.path.join(BUILD, CFG["slug"])
    for d in (tmp, plugin_dir):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(tmp)
    fonts_dir = os.path.join(plugin_dir, "assets", "fonts")
    os.makedirs(fonts_dir)

    cmap = set(TTFont(CFG["static_src"][400], recalcTimestamp=False).getBestCmap())
    slices = plan_slices(cmap)
    json.dump({n: "".join(map(chr, c)) for n, c in slices},
              open(os.path.join(BUILD, "slices.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)

    manifest = {"version": args.version, "family": CFG["family"], "preload": [], "weights": {}}
    faces, tail_faces = [], []
    for weight in WEIGHTS:
        inst = TTFont(CFG["static_src"][weight], recalcTimestamp=False)
        rename(inst, weight)
        inst_path = os.path.join(tmp, f"static-{weight}.ttf")
        inst.save(inst_path)
        entries = []
        for name, cps in slices:
            data = subset_woff2(inst_path, cps)
            fname = f"{CFG['prefix']}-{weight}-{name}.{hashlib.sha256(data).hexdigest()[:8]}.woff2"
            open(os.path.join(fonts_dir, fname), "wb").write(data)
            entries.append({"slice": name, "file": fname, "chars": len(cps), "bytes": len(data)})
            # u* slices cover characters rarely used; their long ranges go to a non-blocking stylesheet.
            (tail_faces if name.startswith("u") else faces).append(
                '@font-face{font-family:"%s";font-style:normal;font-weight:%d;font-display:swap;'
                'src:url(fonts/%s) format("woff2");unicode-range:%s}' % (CFG["family"], weight, fname, unicode_range(cps)))
            print(f"{weight} {name:4} {len(cps):5} chars {len(data)/1024:8.1f} KB", flush=True)
        manifest["weights"][str(weight)] = entries
        if weight == 400:
            manifest["preload"] += [e["file"] for e in entries if e["slice"] in ("l0", "h0")]

    css = "\n".join(faces) + "\n"
    open(os.path.join(plugin_dir, "assets", "cq.css"), "w", encoding="utf-8").write(css)
    tail_css = "\n".join(tail_faces) + "\n"
    open(os.path.join(plugin_dir, "assets", "cq-tail.css"), "w", encoding="utf-8").write(tail_css)
    php = open(os.path.join(CFG["plugin"], CFG["php"]), encoding="utf-8").read()
    open(os.path.join(plugin_dir, CFG["php"]), "w", encoding="utf-8").write(php.replace("{{VERSION}}", args.version))
    shutil.copy(CFG["ofl"], os.path.join(plugin_dir, "OFL.txt"))
    shutil.copy(os.path.join(CFG["plugin"], "readme.txt"), plugin_dir)
    for extra in CFG["extra_files"]:
        src = os.path.join(CFG["plugin"], extra)
        (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(plugin_dir, extra))
    json.dump(manifest, open(os.path.join(plugin_dir, "manifest.json"), "w"), indent=1)

    zpath = os.path.join(BUILD, f"{CFG['slug']}-{args.version}.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in sorted(os.walk(plugin_dir)):
            for f in sorted(files):
                full = os.path.join(base, f)
                z.write(full, os.path.relpath(full, BUILD))
    shutil.rmtree(tmp)

    br = lambda s: len(brotli.compress(s.encode(), quality=11)) / 1024
    lines = [f"# {CFG['family']} build {args.version}", ""]
    for w, es in manifest["weights"].items():
        tot = sum(e["bytes"] for e in es)
        hot = sum(e["bytes"] for e in es if e["slice"] in ("l0", "h0"))
        lines.append(f"- weight {w}: {len(es)} slices, total {tot/1024/1024:.2f} MB, preloaded slices {hot/1024:.1f} KB")
    lines.append(f"- cq.css (render-blocking): {len(css.encode())/1024:.1f} KB, brotli {br(css):.1f} KB")
    lines.append(f"- cq-tail.css (non-blocking): {len(tail_css.encode())/1024:.1f} KB, brotli {br(tail_css):.1f} KB")
    lines.append(f"- zip: {os.path.getsize(zpath)/1024/1024:.2f} MB")
    lines += ["", "| slice | chars | 400 KB | 700 KB |", "|---|---|---|---|"]
    for e4, e7 in zip(manifest["weights"]["400"], manifest["weights"]["700"]):
        lines.append(f"| {e4['slice']} | {e4['chars']} | {e4['bytes']/1024:.1f} | {e7['bytes']/1024:.1f} |")
    open(os.path.join(BUILD, "build-report.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:8]))


if __name__ == "__main__":
    main()
