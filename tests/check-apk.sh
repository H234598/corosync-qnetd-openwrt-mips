#!/usr/bin/env bash
set -euo pipefail

sdk_dir=${1:?SDK directory required}
output_dir=${2:?output directory required}
apk_bin="$sdk_dir/staging_dir/host/bin/apk"
test -x "$apk_bin"
shopt -s nullglob
apks=("$output_dir"/corosync-qnetd-*.apk)
test ${#apks[@]} -eq 1

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
"$apk_bin" --allow-untrusted mkndx --output "$tmpdir/packages.adb" "${apks[0]}"
mkdir -p "$tmpdir/root/lib/apk/db" "$tmpdir/root/etc/apk" "$tmpdir/files"
touch "$tmpdir/root/lib/apk/db/installed" "$tmpdir/root/etc/apk/world"
pkginfo=$("$apk_bin" --root "$tmpdir/root" --repository "$tmpdir/packages.adb" --allow-untrusted \
	query --available --fields name,version,arch,depends --format yaml corosync-qnetd)
grep -Eq '^- name: corosync-qnetd$' <<<"$pkginfo"
grep -Eq '^  version: 3\.0\.4-r[0-9]+$' <<<"$pkginfo"
grep -Eq '^  arch: mips_24kc$' <<<"$pkginfo"
for dependency in libnss nspr nss-utils openssl-util bash coreutils-chown coreutils-stat coreutils-sha1sum procps-ng-ps procps-ng-w openssh-sftp-server; do
	grep -Eq "^    - ${dependency}([<>=~].*)?$" <<<"$pkginfo"
done
if grep -Eq '^    - (libknet|libqb|corosync-nss-tools)([<>=~].*)?$' <<<"$pkginfo"; then
	exit 1
fi
"$apk_bin" --allow-untrusted extract --no-chown --destination "$tmpdir/files" "${apks[0]}"
if find "$tmpdir/files" -type f | grep -Eq '\.(a|o|la|h)$'; then
	exit 1
fi
test -x "$tmpdir/files/usr/sbin/corosync-qnetd-certutil"
test -x "$tmpdir/files/etc/init.d/corosync-qnetd"
grep -Fq 'corosync-qnetd -f -l 192.168.62.11' "$tmpdir/files/etc/init.d/corosync-qnetd"
if find "$tmpdir/files" -type f -name '*.so*' | grep -q .; then
	exit 1
fi
