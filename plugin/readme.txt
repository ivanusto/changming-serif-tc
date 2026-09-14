=== ChangMing Webfont（昌明體） ===
Requires at least: 6.0
Requires PHP: 7.4
License: GPL-2.0-or-later (code), OFL-1.1 (fonts)

Self-hosted 昌明體 ChangMing Serif TC for Traditional Chinese WordPress sites.
A humanist serif: softened triangular serifs, rounded stroke turns and lower
stroke contrast than a publishing Mincho. Weights 400 and 700, sliced by
unicode-range so browsers only download the characters a page uses.

== Settings ==
Settings > 昌明體: apply to body text and/or headings, heading weight (400 or
700), extra selectors for theme-specific elements, force (!important), Latin
font (昌明體 or your own stack) and preload. JNews titles and Elementor global
typography are handled automatically when detected.

== Font license ==
昌明體 ChangMing Serif TC is a modified version of Noto Serif TC.
Copyright (c) 2017-2024 Adobe (http://www.adobe.com/). Noto is a trademark of
Google Inc. Licensed under the SIL Open Font License, Version 1.1 (see
OFL.txt, https://openfontlicense.org).

Modifications: instanced from weights 300 and 600; outlines morphed with an
opening of radius 10, a closing of radius 12 (400) or 14 (700) and a
thickening of 7 (400) or 12 (700) font units, to soften the serifs, round the
stroke turns and reduce stroke contrast; renamed; subset and sliced by
unicode-range. The fonts are distributed under the OFL only and are not sold
by themselves.

== Uninstall and rollback ==
Deactivate the plugin, or add define('CHANGMING_WEBFONT_DISABLE', true); to
wp-config.php. Deleting the plugin removes its single option
(changming_webfont).
