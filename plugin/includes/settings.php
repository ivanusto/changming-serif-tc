<?php
/**
 * Settings > 昌明體: where and how the font applies.
 */

defined( 'ABSPATH' ) || exit;

function changming_webfont_defaults() {
	return array(
		'body'            => 1,
		'headings'        => 1,
		'heading_weight'  => 700,
		'extra_selectors' => '',
		'force'           => 0,
		'latin'           => 'changming',
		'latin_stack'     => '',
		'preload'         => 1,
	);
}

function changming_webfont_options() {
	$saved = get_option( 'changming_webfont', array() );
	return array_merge( changming_webfont_defaults(), is_array( $saved ) ? $saved : array() );
}

/**
 * Strip anything that could close a rule or start a new one; values end up inside generated CSS.
 */
function changming_webfont_clean_css_fragment( $value, $pattern ) {
	$value = str_replace( array( '/*', '*/' ), '', (string) $value );
	$value = preg_replace( $pattern, '', $value );
	return trim( $value );
}

function changming_webfont_sanitize( $input ) {
	$input = is_array( $input ) ? $input : array();
	$out   = changming_webfont_defaults();

	foreach ( array( 'body', 'headings', 'force', 'preload' ) as $flag ) {
		$out[ $flag ] = empty( $input[ $flag ] ) ? 0 : 1;
	}
	$out['heading_weight'] = ( isset( $input['heading_weight'] ) && 400 === (int) $input['heading_weight'] ) ? 400 : 700;
	$out['latin']          = ( isset( $input['latin'] ) && 'custom' === $input['latin'] ) ? 'custom' : 'changming';

	$selectors = changming_webfont_clean_css_fragment( $input['extra_selectors'] ?? '', '/[{}<>;@\\\\]/' );
	$out['extra_selectors'] = substr( implode( "\n", changming_webfont_selector_list( $selectors ) ), 0, 2000 );

	// Font names only: letters, digits, spaces, quotes, commas, hyphens, underscores, dots.
	$stack = changming_webfont_clean_css_fragment( $input['latin_stack'] ?? '', '/[^\p{L}\p{N}\s,\'"_\-\.]/u' );
	$out['latin_stack'] = substr( $stack, 0, 300 );

	return $out;
}

add_action( 'admin_init', function () {
	register_setting( 'changming_webfont', 'changming_webfont', array(
		'type'              => 'array',
		'sanitize_callback' => 'changming_webfont_sanitize',
		'default'           => changming_webfont_defaults(),
	) );
} );

add_action( 'admin_menu', function () {
	add_options_page( '昌明體', '昌明體', 'manage_options', 'changming-webfont', 'changming_webfont_render_settings' );
} );

function changming_webfont_render_settings() {
	if ( ! current_user_can( 'manage_options' ) ) {
		return;
	}
	$o    = changming_webfont_options();
	$name = 'changming_webfont';
	?>
	<div class="wrap">
		<h1>昌明體 ChangMing Serif TC</h1>
		<form method="post" action="options.php">
			<?php settings_fields( 'changming_webfont' ); ?>
			<table class="form-table" role="presentation">
				<tr>
					<th scope="row">套用範圍</th>
					<td>
						<label><input type="checkbox" name="<?php echo esc_attr( $name ); ?>[body]" value="1" <?php checked( $o['body'], 1 ); ?>> 內文（body、按鈕與表單欄位）</label><br>
						<label><input type="checkbox" name="<?php echo esc_attr( $name ); ?>[headings]" value="1" <?php checked( $o['headings'], 1 ); ?>> 標題（h1 到 h6、文章與區塊標題；JNews 標題自動加入）</label>
					</td>
				</tr>
				<tr>
					<th scope="row">標題字重</th>
					<td>
						<label><input type="radio" name="<?php echo esc_attr( $name ); ?>[heading_weight]" value="700" <?php checked( (int) $o['heading_weight'], 700 ); ?>> 700 粗</label>
						<label style="margin-left:1em"><input type="radio" name="<?php echo esc_attr( $name ); ?>[heading_weight]" value="400" <?php checked( (int) $o['heading_weight'], 400 ); ?>> 400 一般</label>
						<p class="description">字型只有 400 與 700 兩個字重。</p>
					</td>
				</tr>
				<tr>
					<th scope="row"><label for="changming-extra">額外選擇器</label></th>
					<td>
						<textarea id="changming-extra" class="large-text code" rows="4" name="<?php echo esc_attr( $name ); ?>[extra_selectors]"><?php echo esc_textarea( $o['extra_selectors'] ); ?></textarea>
						<p class="description">佈景主題自己指定字型、沒有被換到的元素，一行一個，例如 <code>.post-card__title</code>。</p>
					</td>
				</tr>
				<tr>
					<th scope="row">強制套用</th>
					<td><label><input type="checkbox" name="<?php echo esc_attr( $name ); ?>[force]" value="1" <?php checked( $o['force'], 1 ); ?>> 規則加上 <code>!important</code>（佈景主題權重較高、仍沒換到時才開）</label></td>
				</tr>
				<tr>
					<th scope="row">英文字型</th>
					<td>
						<label><input type="radio" name="<?php echo esc_attr( $name ); ?>[latin]" value="changming" <?php checked( $o['latin'], 'changming' ); ?>> 也用昌明體（中英文風格一致）</label><br>
						<label><input type="radio" name="<?php echo esc_attr( $name ); ?>[latin]" value="custom" <?php checked( $o['latin'], 'custom' ); ?>> 使用下列英文字型，中文仍用昌明體</label><br>
						<input type="text" class="regular-text" name="<?php echo esc_attr( $name ); ?>[latin_stack]" value="<?php echo esc_attr( $o['latin_stack'] ); ?>" placeholder='"Helvetica Neue", Arial'>
					</td>
				</tr>
				<tr>
					<th scope="row">預載字型</th>
					<td><label><input type="checkbox" name="<?php echo esc_attr( $name ); ?>[preload]" value="1" <?php checked( $o['preload'], 1 ); ?>> 預先載入英文與最常用中文切片（建議開啟）</label></td>
				</tr>
			</table>
			<?php submit_button(); ?>
		</form>
		<h2>目前產生的 CSS</h2>
		<pre style="background:#fff;border:1px solid #ccd0d4;padding:12px;white-space:pre-wrap"><?php echo esc_html( changming_webfont_css_rules( $o ) ); ?></pre>
	</div>
	<?php
}
