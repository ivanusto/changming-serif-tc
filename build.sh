#!/bin/sh
# Full build: download sources, instance, add Taiwanese and Hakka glyphs, morph, QA, then slice and package.
# usage: ./build.sh 1.1.0        (SKIP_QA=1 skips the ~10 minute outline check)
set -eu
cd "$(dirname "$0")"
VERSION="${1:?usage: ./build.sh <version>}"

# Base: google/fonts commit 6d17dab13b85129360f9748f057c7f67c5f484d4.
SRC="work/NotoSerifTC[wght].ttf"
SRC_URL="https://raw.githubusercontent.com/google/fonts/6d17dab13b85129360f9748f057c7f67c5f484d4/ofl/notoseriftc/NotoSerifTC%5Bwght%5D.ttf"
SRC_SHA256="0077e18f57c6908f4a000969880940bdb0dad057c0e8d98b49dc364c3d1b09c6"

# Supplement layer 2: Noto Serif CJK TC 2.003, the full Source Han Serif inventory with the same outlines.
CJK_ZIP="work/03_NotoSerifCJK-TTF-VF.zip"
CJK_URL="https://github.com/notofonts/noto-cjk/releases/download/Serif2.003/03_NotoSerifCJK-TTF-VF.zip"
CJK_SHA256="ad58364bca7c70a15b40e941df0ce0da85b1e4a882ab176f14e661cf1a0af05e"
CJK="work/NotoSerifCJKtc-VF.ttf"

# Supplement layer 3: GenYo Min 2 TW v2.100, Taiwanese and Hakka hanzi and romanisation marks.
GENYO_ZIP="work/GenYoMin2TW-otf.zip"
GENYO_URL="https://github.com/ButTaiwan/genyo-font/releases/download/v2.100/GenYoMin2TW-otf.zip"
GENYO_SHA256="64ed21a2ef3b42171bdded55a705b32cc105740436c9f61c3d6efec95a769718"
GENYO_300="work/GenYoMin2TW-L.otf"
GENYO_600="work/GenYoMin2TW-SB.otf"

mkdir -p work build
[ -f "$SRC" ] || curl -fL -o "$SRC" "$SRC_URL"
echo "$SRC_SHA256  $SRC" | sha256sum -c -
[ -f "$CJK_ZIP" ] || curl -fL -o "$CJK_ZIP" "$CJK_URL"
echo "$CJK_SHA256  $CJK_ZIP" | sha256sum -c -
[ -f "$CJK" ] || unzip -o -j "$CJK_ZIP" "Variable/TTF/NotoSerifCJKtc-VF.ttf" -d work
[ -f "$GENYO_ZIP" ] || curl -fL -o "$GENYO_ZIP" "$GENYO_URL"
echo "$GENYO_SHA256  $GENYO_ZIP" | sha256sum -c -
[ -f "$GENYO_300" ] && [ -f "$GENYO_600" ] || unzip -o -j "$GENYO_ZIP" "*$(basename "$GENYO_300")" "*$(basename "$GENYO_600")" -d work

docker build -q -t changming-serif-tc-build . >/dev/null
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e SKIP_QA="${SKIP_QA:-0}" -e MORPH_PROCS="${MORPH_PROCS:-}" \
  -v "$PWD":/w -w /w changming-serif-tc-build sh -c "
set -e
python tools/morph.py instance '$SRC' 300 work/noto-300.ttf
python tools/morph.py instance '$SRC' 600 work/noto-600.ttf
python tools/morph.py instance '$CJK' 300 work/cjk-300.ttf
python tools/morph.py instance '$CJK' 600 work/cjk-600.ttf
python tools/merge_supplement.py work/noto-300.ttf work/base-300.ttf build/supplement-400.json work/cjk-300.ttf '$GENYO_300'
python tools/merge_supplement.py work/noto-600.ttf work/base-600.ttf build/supplement-700.json work/cjk-600.ttf '$GENYO_600'
python tools/morph.py rebuild work/base-300.ttf work/morph-400.ttf '{\"opening\":10,\"closing\":12,\"thicken\":7}'
python tools/morph.py rebuild work/base-600.ttf work/morph-700.ttf '{\"opening\":10,\"closing\":14,\"thicken\":12}'
if [ \"\$SKIP_QA\" != 1 ]; then
  python tools/qa.py work/base-300.ttf work/morph-400.ttf work/qa-400.json 25
  python tools/qa.py work/base-600.ttf work/morph-700.ttf work/qa-700.json 32
fi
python tools/build.py --version $VERSION
"
