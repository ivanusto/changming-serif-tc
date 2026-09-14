#!/bin/sh
# Full build: download Noto Serif TC, instance, morph, QA, then slice and package the WordPress plugin.
# usage: ./build.sh 1.0.1        (SKIP_QA=1 skips the ~10 minute outline check)
set -eu
cd "$(dirname "$0")"
VERSION="${1:?usage: ./build.sh <version>}"

# Pinned source: google/fonts commit 6d17dab13b85129360f9748f057c7f67c5f484d4.
SRC="work/NotoSerifTC[wght].ttf"
SRC_URL="https://raw.githubusercontent.com/google/fonts/6d17dab13b85129360f9748f057c7f67c5f484d4/ofl/notoseriftc/NotoSerifTC%5Bwght%5D.ttf"
SRC_SHA256="0077e18f57c6908f4a000969880940bdb0dad057c0e8d98b49dc364c3d1b09c6"

mkdir -p work build
[ -f "$SRC" ] || curl -fL -o "$SRC" "$SRC_URL"
echo "$SRC_SHA256  $SRC" | sha256sum -c -

docker build -q -t changming-serif-tc-build . >/dev/null
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e SKIP_QA="${SKIP_QA:-0}" \
  -v "$PWD":/w -w /w changming-serif-tc-build sh -c "
set -e
python tools/morph.py instance '$SRC' 300 work/base-300.ttf
python tools/morph.py instance '$SRC' 600 work/base-600.ttf
python tools/morph.py rebuild work/base-300.ttf work/morph-400.ttf '{\"opening\":10,\"closing\":12,\"thicken\":7}'
python tools/morph.py rebuild work/base-600.ttf work/morph-700.ttf '{\"opening\":10,\"closing\":14,\"thicken\":12}'
if [ \"\$SKIP_QA\" != 1 ]; then
  python tools/qa.py work/base-300.ttf work/morph-400.ttf work/qa-400.json 25
  python tools/qa.py work/base-600.ttf work/morph-700.ttf work/qa-700.json 32
fi
python tools/build.py --version $VERSION
"
