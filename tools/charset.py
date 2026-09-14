"""Build data/taigi-hakka.json: characters needed to typeset Taiwanese Hokkien and Hakka.

Sources, pinned:
  MoE Dictionary of Frequently-Used Taiwanese, ChhoeTaigi CSV (some hanzi still in the MoE private use area)
    https://raw.githubusercontent.com/ChhoeTaigi/ChhoeTaigiDatabase/b33c6a1fcc2d11a2962e76b6055d528d11677c3b/ChhoeTaigiDatabase/ChhoeTaigi_KauiokpooTaigiSutian.csv
  MoE Dictionary of Frequently-Used Taiwanese, g0v conversion to Unicode, and its private use area table
    https://raw.githubusercontent.com/g0v/moedict-data-twblg/4626bfcfccd6087496d14aac702b5e8a6a82e974/dict-twblg.json
    https://raw.githubusercontent.com/g0v/moedict-data-twblg/4626bfcfccd6087496d14aac702b5e8a6a82e974/x-%E9%80%A0%E5%AD%97.csv
  MoE Dictionary of Frequently-Used Taiwan Hakka (g0v moedict-data-hakka)
    https://raw.githubusercontent.com/g0v/moedict-data-hakka/c1a28576be319d5e53190d8ba8e969158e86952c/dict-hakka.json

usage: python tools/charset.py ChhoeTaigi_KauiokpooTaigiSutian.csv dict-twblg.json x-造字.csv dict-hakka.json > data/taigi-hakka.json
"""
import csv
import json
import re
import sys
import unicodedata


def is_han(cp):
    return 0x3400 <= cp <= 0x4DBF or 0x4E00 <= cp <= 0x9FFF or 0xF900 <= cp <= 0xFAFF or 0x20000 <= cp <= 0x323AF


def is_pua(cp):
    return 0xE000 <= cp <= 0xF8FF or cp >= 0xF0000


def is_roman(ch):
    """Letters, combining tone marks and superscript tone digits used by romanisations (not ASCII, not CJK)."""
    cp = ord(ch)
    if cp <= 0x7E or cp >= 0x3000:
        return False
    cat = unicodedata.category(ch)
    # Me excluded: the Hakka dictionary wraps dialect labels in enclosing keycaps.
    return cat[0] == "L" or cat in ("Mn", "Mc") or (cat == "No" and "SUPERSCRIPT" in unicodedata.name(ch, ""))


def main(taigi_csv, twblg_json, pua_csv, hakka_json):
    pua = {chr(int(row["造字碼"], 16)): row["對應字"] for row in csv.DictReader(open(pua_csv, encoding="utf-8-sig"))}
    unmapped = set()

    def han_of(text):
        out = set()
        for c in text:
            if is_pua(ord(c)):
                if c in pua:
                    out.add(ord(pua[c]))
                else:
                    unmapped.add(f"U+{ord(c):04X}")
            elif is_han(ord(c)):
                out.add(ord(c))
        return out

    taigi, hakka, roman = set(), set(), set()
    for row in csv.DictReader(open(taigi_csv, encoding="utf-8-sig")):
        for key in ("HanLoTaibunKip", "KipDictHanjiTaibunOthers"):
            taigi |= han_of(row[key])
        for key in ("PojUnicode", "PojUnicodeOthers", "KipUnicode", "KipUnicodeOthers",
                    "HanLoTaibunKip", "KaisoehHanLoPoj", "KaisoehHanLoKip"):
            roman.update(ord(c) for c in row[key] if is_roman(c))
    for entry in json.load(open(twblg_json, encoding="utf-8")):
        taigi |= han_of(entry["title"])
        for het in entry.get("heteronyms", []):
            for d in het.get("definitions", []):
                # Examples are "￹Taiwanese hanzi￺romanisation￻Mandarin"; keep the first part only.
                for ex in d.get("example", []):
                    m = re.match("￹([^￺￻]*)", ex)
                    if m:
                        taigi |= han_of(m.group(1))
    for entry in json.load(open(hakka_json, encoding="utf-8")):
        hakka |= han_of(entry["title"])
        for het in entry.get("heteronyms", []):
            roman.update(ord(c) for c in het.get("pinyin", "") if is_roman(c))
            for d in het.get("definitions", []):
                hakka |= han_of("".join(d.get("example", [])) + d.get("def", ""))
    if unmapped:
        sys.exit(f"private use characters without a mapping: {' '.join(sorted(unmapped))}")
    # Bopomofo with the extensions for Taiwanese and Hakka (方音符號).
    bopomofo = set(range(0x3105, 0x3130)) | set(range(0x31A0, 0x31C0))
    out = {name: "".join(map(chr, sorted(s))) for name, s in
           (("taigi_han", taigi), ("hakka_han", hakka), ("romanization", roman), ("bopomofo", bopomofo))}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=0)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main(*sys.argv[1:5])
