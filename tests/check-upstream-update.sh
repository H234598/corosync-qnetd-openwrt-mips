#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd "$(dirname "$0")/.." && pwd)
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

makefile="$tmp_dir/Makefile"
archive="$tmp_dir/source.tar.gz"
outputs="$tmp_dir/outputs"
printf '%s\n' \
	'PKG_VERSION:=3.0.4' \
	'PKG_RELEASE:=7' \
	'PKG_HASH:=old' > "$makefile"
printf '%s\n' fixture > "$archive"

QDEVICE_TAG=v3.0.5 QDEVICE_ARCHIVE="$archive" GITHUB_OUTPUT="$outputs" \
	bash "$repo_dir/scripts/update-upstream.sh" "$makefile"
expected_hash=$(sha256sum "$archive" | cut -d' ' -f1)
grep -qx 'PKG_VERSION:=3.0.5' "$makefile"
grep -qx 'PKG_RELEASE:=1' "$makefile"
grep -qx "PKG_HASH:=$expected_hash" "$makefile"
grep -qx 'updated=true' "$outputs"
grep -qx 'release_tag=v3.0.5-r1' "$outputs"

: > "$outputs"
QDEVICE_TAG=v3.0.5 GITHUB_OUTPUT="$outputs" \
	bash "$repo_dir/scripts/update-upstream.sh" "$makefile"
grep -qx 'updated=false' "$outputs"

if QDEVICE_TAG=v3.0.4 bash "$repo_dir/scripts/update-upstream.sh" "$makefile" >/dev/null 2>&1; then
	echo 'Downgrade was accepted.' >&2
	exit 1
fi

if QDEVICE_TAG=v3.0.6-rc1 bash "$repo_dir/scripts/update-upstream.sh" "$makefile" >/dev/null 2>&1; then
	echo 'Prerelease tag was accepted.' >&2
	exit 1
fi

echo 'Upstream update checks passed.'
