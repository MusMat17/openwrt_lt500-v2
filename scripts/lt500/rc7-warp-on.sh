_st_warp_on() {
	local priv peer
	if _st_warp_ext; then
		[ "$(uci -q get "network.$ST_WARP_IF.proto")" = amneziawg ]
		return $?
	fi
	[ -s "$ST_WARP_CONF" ] || return 1
	_st_owns "net $ST_WARP_IF" && return 0
	[ "$(uci -q get "network.$ST_WARP_IF.proto")" = amneziawg ] || return 1
	priv="$(sed -n 's/^[[:space:]]*PrivateKey[[:space:]]*=[[:space:]]*//p' "$ST_WARP_CONF" | head -n1)"
	peer="$(sed -n 's/^[[:space:]]*PublicKey[[:space:]]*=[[:space:]]*//p' "$ST_WARP_CONF" | head -n1)"
	[ -n "$priv" ] && [ "$priv" = "$(uci -q get "network.$ST_WARP_IF.private_key")" ] || return 1
	[ -n "$peer" ] && [ "$peer" = "$(uci -q get "network.$ST_WARP_IF"_peer.public_key)" ] || return 1
	_st_own "net $ST_WARP_IF"
}
