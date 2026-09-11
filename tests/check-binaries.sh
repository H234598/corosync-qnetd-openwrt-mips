#!/usr/bin/env bash
set -euo pipefail

sdk_dir=${1:?SDK directory required}
output_dir=${2:?output directory required}
readelf_bin=$(find "$sdk_dir/staging_dir" -type f -path '*/toolchain-*/bin/*-linux-musl-readelf' -print -quit)
apk_bin="$sdk_dir/staging_dir/host/bin/apk"
test -n "$readelf_bin"
test -x "$apk_bin"

check_mips_be() {
	local binary=$1
	local file_output
	file_output=$(file -b "$binary")
	echo "$file_output" | grep -Eq 'ELF 32-bit MSB.*MIPS'
	if echo "$file_output" | grep -Eqi 'mipsel|LSB|aarch64|x86-64|x86-32|glibc'; then
		exit 1
	fi
	"$readelf_bin" -h "$binary" | grep -Eq 'Class:.*ELF32'
	"$readelf_bin" -h "$binary" | grep -Eq 'Data:.*big endian'
	if "$readelf_bin" -d "$binary" | grep -Eq '\((RPATH|RUNPATH)\)'; then
		exit 1
	fi
}

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
for apk in "$output_dir"/corosync-qnetd-*.apk; do
	[ -f "$apk" ] || continue
	"$apk_bin" --allow-untrusted extract --no-chown --destination "$tmpdir" "$apk"
done

for binary in "$tmpdir"/usr/sbin/corosync-qnetd "$tmpdir"/usr/sbin/corosync-qnetd-tool; do
	test -x "$binary"
	check_mips_be "$binary"
	if "$readelf_bin" -l "$binary" | grep -Eq 'ld-linux|glibc'; then
		exit 1
	fi
done

qnetd="$tmpdir/usr/sbin/corosync-qnetd"
"$readelf_bin" -d "$qnetd" | grep -Eq '\(NEEDED\).*\[libnss3\.so\]'
"$readelf_bin" -d "$qnetd" | grep -Eq '\(NEEDED\).*\[libssl3\.so\]'

nss_dir=$(find "$sdk_dir/staging_dir" -type d -path '*/usr/lib/nss-qnetd' -print -quit)
test -n "$nss_dir"
for library in libnss3.so libssl3.so libsmime3.so libnssutil3.so libsoftokn3.so libfreebl3.so; do
	test -f "$nss_dir/$library"
	check_mips_be "$nss_dir/$library"
done
