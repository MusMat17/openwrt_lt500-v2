# Recover automatic WARP interfaces left behind by an older panel removal.
# UCI holds the keys actually used by the working interface. Never log them.
_st_warp_recover_if() {
	local wi="$1" conf="$2" ps priv peer addr desc ck cp tmp key opt value
	case "$wi" in zmwarp|zmwarp2|zmwarp3) ;; *) return 1 ;; esac
	[ "$(uci -q get "network.$wi.proto")" = amneziawg ] || return 1
	ps="${wi}_peer"
	[ "$(uci -q get "network.$ps")" = "amneziawg_$wi" ] || return 1
	peer="$(uci -q get "network.$ps.public_key")"
	[ "$peer" = 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=' ] || return 1
	priv="$(uci -q get "network.$wi.private_key")"
	printf '%s\n' "$priv" | grep -qE '^[A-Za-z0-9+/]{43}=$' || return 1
	addr="$(uci -q get "network.$wi.addresses" | tr ' ' ',')"
	printf '%s\n' "$addr" | grep -qE '^[0-9A-Fa-f:./,]+$' || return 1
	if ! _st_owns "net $wi"; then
		# Reserved name alone is insufficient: require the original panel peer
		# type, description, Cloudflare key and split-routing setting as well.
		desc="$(uci -q get "network.$ps.description")"
		case "$wi:$desc" in 'zmwarp:WARP '|zmwarp:WARP|'zmwarp:WARP 1'|'zmwarp2:WARP 2'|'zmwarp3:WARP 3') ;; *) return 1 ;; esac
		[ "$(uci -q get "network.$ps.route_allowed_ips")" = 0 ] || return 1
	fi
	ck="$(sed -n 's/^[[:space:]]*PrivateKey[[:space:]]*=[[:space:]]*//p' "$conf" 2>/dev/null | head -n1)"
	cp="$(sed -n 's/^[[:space:]]*PublicKey[[:space:]]*=[[:space:]]*//p' "$conf" 2>/dev/null | head -n1)"
	if [ "$ck" != "$priv" ] || [ "$cp" != "$peer" ]; then
		mkdir -p "$ST_DIR" || return 1
		tmp="$(umask 077; mktemp "$ST_DIR/.warp-recover.XXXXXX")" || return 1
		{
			printf '[Interface]\nPrivateKey = %s\nAddress = %s\n' "$priv" "$addr"
			for key in MTU Jc Jmin Jmax S1 S2 H1 H2 H3 H4 I1; do
				opt="$(printf '%s' "$key" | tr 'A-Z' 'a-z')"
				[ "$key" = MTU ] || opt="awg_$opt"
				value="$(uci -q get "network.$wi.$opt")"
				[ -z "$value" ] || printf '%s = %s\n' "$key" "$value"
			done
			printf '\n[Peer]\nPublicKey = %s\nAllowedIPs = 0.0.0.0/0\nEndpoint = engage.cloudflareclient.com:4500\nPersistentKeepalive = 25\n' "$peer"
		} > "$tmp" || { rm -f "$tmp"; return 1; }
		if [ -s "$conf" ] && [ ! -e "$conf.before-recovery" ]; then
			(umask 077; cat "$conf" > "$conf.before-recovery") || { rm -f "$tmp"; return 1; }
			chmod 600 "$conf.before-recovery"
		fi
		mv -f "$tmp" "$conf" || { rm -f "$tmp"; return 1; }
	fi
	_st_own "net $wi"
}

_st_warp_recover_all() {
	local ri rcfile
	for ri in zmwarp zmwarp2 zmwarp3; do
		case "$ri" in zmwarp) rcfile="$ST_DIR/warp.conf" ;; *) rcfile="$ST_DIR/warp${ri#zmwarp}.conf" ;; esac
		_st_warp_recover_if "$ri" "$rcfile" || :
	done
}
