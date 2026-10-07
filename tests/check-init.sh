#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd "$(dirname "$0")/.." && pwd)
init_script=${1:-$repo_dir/package/corosync-qnetd/files/qnetd.init}
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

# Exercise the init script with the same POSIX shell syntax and a minimal
# UCI/procd boundary. No daemon or network service is started by this test.
for address in '' 0.0.0.0 0 0x0 000.000.000.000 :: '[::]' ::0 0:0:0:0:0:0:0:0 \
	2001:db8::10 router.example.org 192.0.2 192.0.2.256 192.0.02.10 \
	192.0.2.10. .192.0.2.10 192..2.10 '192.0.2.10 extra' 192.0.2.10; do
	: > "$tmp_dir/procd-calls"
	if LISTEN_ADDRESS="$address" CALL_LOG="$tmp_dir/procd-calls" \
		sh -s "$init_script" > "$tmp_dir/stdout" 2> "$tmp_dir/stderr" <<'SH'
config_load() { [ "$1" = corosync-qnetd ]; }
config_get() {
	[ "$1" = listen_address ] && [ "$2" = main ] && [ "$3" = listen_address ] || return 1
	listen_address=$LISTEN_ADDRESS
}
procd_open_instance() { printf '%s\n' open >> "$CALL_LOG"; }
procd_set_param() { printf '<%s>' "$@" >> "$CALL_LOG"; printf '\n' >> "$CALL_LOG"; }
procd_close_instance() { printf '%s\n' close >> "$CALL_LOG"; }
procd_add_reload_trigger() { printf 'reload <%s>\n' "$1" >> "$CALL_LOG"; }
. "$1"
start_service || exit "$?"
service_triggers
SH
	then
		case "$address" in
			192.0.2.10) ;;
			*) echo 'Init accepted an unset or wildcard address.' >&2; exit 1 ;;
		esac
		grep -Fxq "<command></usr/sbin/corosync-qnetd><-f><-l><$address>" "$tmp_dir/procd-calls"
		grep -Fxq '<respawn>' "$tmp_dir/procd-calls"
		grep -Fxq 'reload <corosync-qnetd>' "$tmp_dir/procd-calls"
	else
		case "$address" in
			192.0.2.10) echo 'Init rejected a configured address.' >&2; exit 1 ;;
			*) ;;
		esac
		test ! -s "$tmp_dir/procd-calls"
		grep -Fq 'Configure a specific local IPv4 listen_address' "$tmp_dir/stderr"
	fi
done

echo 'Init configuration checks passed.'
