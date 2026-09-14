#!/bin/sh
# Functional tests for changming-webfont against the local WordPress (compose project changmingtest, port 8780).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ZIP="${1:?usage: wp_tests.sh path/to/changming-webfont.zip}"
OUT="$HERE/results"
cd "$HERE/wp"
mkdir -p "$OUT"
POST_ID="$(cat "$HERE/.post_id" 2>/dev/null)" || { echo "run tests/setup_wp.sh first" >&2; exit 1; }
URL="http://127.0.0.1:8780/?p=$POST_ID"
pass=0; fail=0
cli() { docker compose -p changmingtest exec -T cli wp "$@"; }
page() { curl -s "$URL&t=$(date +%s%N)"; }
check() { # name, command that must succeed
  if sh -c "$2" >/dev/null 2>&1; then pass=$((pass+1)); echo "PASS $1"; else fail=$((fail+1)); echo "FAIL $1"; fi
}
setopt() { cli option update changming_webfont "$1" --format=json >/dev/null; }

docker compose -p changmingtest cp "$ZIP" cli:/tmp/changming.zip
# Start clean: an earlier run may have left the option behind.
cli option delete changming_webfont >/dev/null 2>&1 || true
cli plugin install /tmp/changming.zip --force >/dev/null
cli plugin activate changming-webfont >/dev/null

page > "$OUT/default.html"
check "preload l0 and h0" "grep -c 'rel=\"preload\"[^>]*changming-webfont/assets/fonts/cmsr-400-' $OUT/default.html | grep -qx 2"
check "font stylesheet" "grep -q \"id='changming-webfont-css'\" $OUT/default.html"
check "tail stylesheet non-blocking" "grep -q \"id='changming-webfont-tail-css'[^>]*media='print' onload=\" $OUT/default.html"
check "inline rules present" "grep -q 'id=.changming-webfont-inline-css' $OUT/default.html"
check "default body rule" "grep -q 'html body,html body button' $OUT/default.html"
check "default heading weight 700" "grep -q 'html body .site-title{font-family:var(--changming-stack);font-weight:700}' $OUT/default.html"
check "default latin stack is ChangMing" "grep -q -- '--changming-stack:\"ChangMing Serif TC\",Georgia' $OUT/default.html"
check "no elementor or jnews rules on twentytwentyfive" "! grep -qE 'elementor-kit|jeg_post_title' $OUT/default.html"

# Settings round trip through the sanitize callback, as the settings form would submit.
cli eval 'update_option("changming_webfont", changming_webfont_sanitize(array("headings"=>"1","heading_weight"=>"400","force"=>"1","latin"=>"custom","latin_stack"=>"\"Helvetica Neue\", Arial; } body{display:none","extra_selectors"=>".post-card__title\n}body{display:none\n.foo@import")));' >/dev/null
cli option get changming_webfont --format=json > "$OUT/options-after-sanitize.json"
page > "$OUT/custom.html"
check "body rule off when unchecked" "! grep -q 'html body,html body button' $OUT/custom.html"
check "heading weight 400 with important" "grep -q 'font-weight:400 !important' $OUT/custom.html"
check "custom latin stack before ChangMing" "grep -q -- '--changming-stack:\"Helvetica Neue\", Arial  bodydisplaynone,\"ChangMing Serif TC\"' $OUT/custom.html || grep -q -- '--changming-stack:\"Helvetica Neue\", Arial' $OUT/custom.html"
check "extra selector is its own rule" "grep -q '^html body .post-card__title{font-family:var(--changming-stack) !important}$' $OUT/custom.html"
sed -n '/changming-webfont-inline-css/,/<\/style>/p' "$OUT/custom.html" > "$OUT/custom-inline.css"
# Injection is neutralised when no declaration can be opened: every rule line has exactly one { and one }, and no @-rules.
check "injection cannot open a declaration" "! grep -qE '\{[^}]*display:none|@import|@font-face' $OUT/custom-inline.css && awk '/^(:root|html body)/{o=gsub(/\{/,\"{\");c=gsub(/\}/,\"}\"); if(o!=1||c!=1) bad=1} END{exit bad}' $OUT/custom-inline.css"
check "saved option values free of CSS control chars" "python3 -c 'import json,sys; o=json.load(open(\"$OUT/options-after-sanitize.json\")); v=o[\"extra_selectors\"]+o[\"latin_stack\"]; sys.exit(any(ch in v for ch in \"{};@<>\\\\\"))'"
cli eval 'update_option("changming_webfont", changming_webfont_sanitize(array("body"=>"1")));' >/dev/null
page > "$OUT/preload-off.html"
check "preload off" "! grep -q 'rel=\"preload\"[^>]*changming' $OUT/preload-off.html && grep -q \"id='changming-webfont-css'\" $OUT/preload-off.html"

# Settings page as admin (cookie login through wp-login.php).
rm -f /tmp/changming-cookies
curl -s -c /tmp/changming-cookies -b 'wordpress_test_cookie=WP%20Cookie%20check' -d 'log=admin&pwd=adminpw&wp-submit=Log+In&testcookie=1' http://127.0.0.1:8780/wp-login.php -o /dev/null
curl -s -b /tmp/changming-cookies 'http://127.0.0.1:8780/wp-admin/options-general.php?page=changming-webfont' > "$OUT/settings-page.html"
check "settings page renders for admin" "grep -q '昌明體 ChangMing Serif TC' $OUT/settings-page.html && grep -q 'name=\"changming_webfont\[heading_weight\]\"' $OUT/settings-page.html && grep -q '_wpnonce' $OUT/settings-page.html"
check "settings page denied when logged out" "! curl -s 'http://127.0.0.1:8780/wp-admin/options-general.php?page=changming-webfont' | grep -q 'changming_webfont\[heading_weight\]'"
check "plugins list has settings link" "curl -s -b /tmp/changming-cookies http://127.0.0.1:8780/wp-admin/plugins.php | grep -q 'options-general.php?page=changming-webfont'"

# Deactivate, then delete: no tags left and option removed.
cli plugin deactivate changming-webfont >/dev/null
check "no tags after deactivate" "! curl -s '$URL&d=1' | grep -q changming"
cli plugin activate changming-webfont >/dev/null
setopt '{"body":1,"headings":1,"heading_weight":700,"extra_selectors":"","force":0,"latin":"changming","latin_stack":"","preload":1}'
# `plugin uninstall` runs uninstall.php like the wp-admin Delete action; `plugin delete` only removes files.
cli plugin uninstall changming-webfont --deactivate >/dev/null
if cli option get changming_webfont >/dev/null 2>&1; then left=yes; else left=no; fi
check "option removed on uninstall" "[ $left = no ]"

echo "passed $pass, failed $fail"
[ "$fail" -eq 0 ]
