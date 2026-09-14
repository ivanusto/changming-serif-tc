#!/bin/sh
# Start a throwaway local WordPress (http://127.0.0.1:8780) and create the test post used by wp_tests.sh.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/wp"
docker compose -p changmingtest up -d
for i in $(seq 1 40); do
  curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8780/ | grep -qE '200|302' && break
  sleep 3
done
docker compose -p changmingtest exec -T cli sh -c '
for i in $(seq 1 30); do wp db check >/dev/null 2>&1 && break; sleep 2; done
wp core is-installed 2>/dev/null || wp core install --url=http://127.0.0.1:8780 --title="昌明體測試" \
  --admin_user=admin --admin_password=adminpw --admin_email=admin@example.test --skip-email >/dev/null
wp option update blogdescription "繁體中文字型測試" >/dev/null
wp post create --post_status=publish --post_title="昌明體測試：鬱鷹靈袋與 English Title" \
  --post_content="<h2>小標題：量化、推論與記憶體頻寬</h2><p>本週重點觀察，研究團隊公布涵蓋九個月的報告，把相關的網路行動攤在陽光下。<strong>地端 AI 工作站</strong>能否長時間穩定運作，取決於散熱與電源。罕用字：鑽齌遳蹤錸匉峁隳褰。</p><p>English text: The quick brown fox jumps over the lazy dog 0123456789.</p>" \
  --porcelain
' | tail -1 > "$HERE/.post_id"
echo "test post id: $(cat "$HERE/.post_id")"
# Tear down with: docker compose -p changmingtest down -v   (run inside tests/wp)
