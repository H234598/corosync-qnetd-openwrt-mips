#!/usr/bin/env bash
set -euo pipefail

makefile=${1:-package/corosync-qnetd/Makefile}

output() {
	[ -z "${GITHUB_OUTPUT:-}" ] || printf '%s=%s\n' "$1" "$2" >> "$GITHUB_OUTPUT"
}

if [ -n "${QDEVICE_TAG:-}" ]; then
	tag=$QDEVICE_TAG
else
	read -r tag draft prerelease < <(
		gh api repos/corosync/corosync-qdevice/releases/latest \
			--jq '[.tag_name, .draft, .prerelease] | @tsv'
	)
	[ "$draft" = false ] && [ "$prerelease" = false ] || {
		echo "Latest upstream release is draft or prerelease: $tag" >&2
		exit 1
	}
fi

version=${tag#v}
[[ $tag == v* && $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
	echo "Unsupported upstream tag: $tag" >&2
	exit 1
}

current=$(sed -n 's/^PKG_VERSION:=//p' "$makefile")
[ -n "$current" ] || {
	echo "PKG_VERSION missing in $makefile" >&2
	exit 1
}

output version "$version"
output upstream_tag "$tag"
output release_tag "v${version}-r1"

if [ "$version" = "$current" ]; then
	output updated false
	echo "Already at corosync-qdevice $version."
	exit 0
fi

newest=$(printf '%s\n%s\n' "$current" "$version" | sort -V | tail -n 1)
[ "$newest" = "$version" ] || {
	echo "Refusing upstream downgrade: $current -> $version" >&2
	exit 1
}

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT
archive="$tmp_dir/corosync-qdevice-$version.tar.gz"

if [ -n "${QDEVICE_ARCHIVE:-}" ]; then
	cp "$QDEVICE_ARCHIVE" "$archive"
else
	curl --fail --location --retry 3 \
		"https://github.com/corosync/corosync-qdevice/archive/refs/tags/$tag/corosync-qdevice-$version.tar.gz" \
		--output "$archive"
fi

hash=$(sha256sum "$archive" | cut -d' ' -f1)
sed -i \
	-e "s/^PKG_VERSION:=.*/PKG_VERSION:=$version/" \
	-e 's/^PKG_RELEASE:=.*/PKG_RELEASE:=1/' \
	-e "s/^PKG_HASH:=.*/PKG_HASH:=$hash/" \
	"$makefile"

output updated true
output source_hash "$hash"
echo "Updated corosync-qdevice: $current -> $version ($hash)"
