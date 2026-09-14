<?php
/**
 * Plugin Name: ChangMing Webfont（昌明體）
 * Plugin URI: https://github.com/ivanusto/changming-serif-tc
 * Description: Self-hosted 昌明體 ChangMing Serif TC, a humanist serif for Traditional Chinese, sliced by unicode-range. Configure under Settings > 昌明體.
 * Version: {{VERSION}}
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * Author: ivanusto
 * Author URI: https://yblog.org
 * License: GPL-2.0-or-later (code), OFL-1.1 (fonts)
 * Text Domain: changming-webfont
 */

defined( 'ABSPATH' ) || exit;

if ( defined( 'CHANGMING_WEBFONT_DISABLE' ) && CHANGMING_WEBFONT_DISABLE ) {
	return;
}

define( 'CHANGMING_WEBFONT_VERSION', '{{VERSION}}' );
define( 'CHANGMING_WEBFONT_FAMILY', 'ChangMing Serif TC' );

require_once __DIR__ . '/includes/settings.php';

function changming_webfont_manifest() {
	static $manifest = null;
	if ( null === $manifest ) {
		$raw      = @file_get_contents( __DIR__ . '/manifest.json' );
		$manifest = $raw ? json_decode( $raw, true ) : array();
	}
	return is_array( $manifest ) ? $manifest : array();
}

/**
 * Split the saved selector list into individual selectors.
 */
function changming_webfont_selector_list( $raw ) {
	$parts = preg_split( '/[,\r\n]+/', (string) $raw );
	return array_values( array_filter( array_map( 'trim', $parts ), 'strlen' ) );
}

/**
 * Build the CSS rules for the current settings. Font faces live in the static stylesheet.
 */
function changming_webfont_css_rules( array $o ) {
	$imp    = ! empty( $o['force'] ) ? ' !important' : '';
	$family = '"' . CHANGMING_WEBFONT_FAMILY . '"';
	if ( 'custom' === $o['latin'] && '' !== $o['latin_stack'] ) {
		// Latin from the site's own stack; CJK has no glyphs there, so it falls through to 昌明體.
		$stack = $o['latin_stack'] . ',' . $family . ',serif';
	} else {
		$stack = $family . ',Georgia,"Times New Roman",serif';
	}

	$rules = array( ':root{--changming-stack:' . $stack . '}' );

	if ( ! empty( $o['body'] ) ) {
		// html prefix: theme CSS may load after this stylesheet, so win on specificity rather than order.
		$rules[] = 'html body,html body button,html body input,html body select,html body textarea{font-family:var(--changming-stack)' . $imp . '}';
	}

	if ( ! empty( $o['headings'] ) ) {
		$headings = array( 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.entry-title', '.wp-block-heading', '.wp-block-post-title', '.site-title' );
		if ( 'jnews' === get_template() ) {
			$headings = array_merge( $headings, array( '.jeg_post_title', '.jeg_post_title a', '.entry-header .jeg_post_title', '.jeg_content .jeg_custom_title_wrapper .jeg_post_title' ) );
		}
		$weight  = 400 === (int) $o['heading_weight'] ? 400 : 700;
		$rules[] = implode( ',', array_map( function ( $s ) {
			return 'html body ' . $s;
		}, $headings ) ) . '{font-family:var(--changming-stack)' . $imp . ';font-weight:' . $weight . $imp . '}';
	}

	// One rule per extra selector: a single invalid selector would otherwise void the whole list.
	foreach ( changming_webfont_selector_list( $o['extra_selectors'] ) as $selector ) {
		$rules[] = 'html body ' . $selector . '{font-family:var(--changming-stack)' . $imp . '}';
	}

	if ( defined( 'ELEMENTOR_VERSION' ) ) {
		$vars = array();
		foreach ( array( 'primary', 'secondary', 'text', 'accent' ) as $slot ) {
			$vars[] = '--e-global-typography-' . $slot . '-font-family:' . $family;
		}
		$rules[] = 'html body[class*="elementor-kit-"]{' . implode( ';', $vars ) . '}';
	}

	return implode( "\n", $rules );
}

add_action( 'wp_enqueue_scripts', function () {
	wp_enqueue_style( 'changming-webfont', plugins_url( 'assets/cq.css', __FILE__ ), array(), CHANGMING_WEBFONT_VERSION );
	wp_add_inline_style( 'changming-webfont', changming_webfont_css_rules( changming_webfont_options() ) );
	wp_enqueue_style( 'changming-webfont-tail', plugins_url( 'assets/cq-tail.css', __FILE__ ), array(), CHANGMING_WEBFONT_VERSION, 'print' );
}, 40 );

// The tail stylesheet only covers characters rarely used, so load it without blocking render.
add_filter( 'style_loader_tag', function ( $tag, $handle ) {
	if ( 'changming-webfont-tail' !== $handle ) {
		return $tag;
	}
	return preg_replace( '/media=([\'"])print\1/', '$0 onload="this.media=\'all\'"', $tag, 1 );
}, 10, 2 );

add_action( 'wp_head', function () {
	$o = changming_webfont_options();
	if ( empty( $o['preload'] ) ) {
		return;
	}
	foreach ( (array) ( changming_webfont_manifest()['preload'] ?? array() ) as $file ) {
		printf(
			'<link rel="preload" href="%s" as="font" type="font/woff2" crossorigin>' . "\n",
			esc_url( plugins_url( 'assets/fonts/' . $file, __FILE__ ) )
		);
	}
}, 1 );

// Keep plugin CSS out of Autoptimize aggregation so relative font URLs and preload URLs stay identical.
add_filter( 'autoptimize_filter_css_exclude', function ( $exclude ) {
	return rtrim( (string) $exclude, ', ' ) . ', changming-webfont/assets/';
} );

add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), function ( $links ) {
	array_unshift( $links, '<a href="' . esc_url( admin_url( 'options-general.php?page=changming-webfont' ) ) . '">' . esc_html__( '設定', 'changming-webfont' ) . '</a>' );
	return $links;
} );
