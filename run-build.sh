#!/usr/bin/env bash
set -euo pipefail

mkdir -p sdk-state/build_dir sdk-state/staging_dir sdk-state/dl output

engine=${CONTAINER_ENGINE:-docker}
if ! command -v "$engine" >/dev/null 2>&1; then
	if command -v podman >/dev/null 2>&1; then
		engine=podman
	else
		echo 'Docker or Podman required.' >&2
		exit 1
	fi
fi

security_args=()
if [ "$engine" = podman ]; then
	security_args+=(--security-opt label=disable)
fi

"$engine" run --rm \
	"${security_args[@]}" \
  -v "$(pwd):/build" \
  -v "$(pwd)/sdk-state/build_dir:/opt/sdk/build_dir" \
  -v "$(pwd)/sdk-state/staging_dir:/opt/sdk/staging_dir/target-mips_24kc_musl" \
  -v "$(pwd)/sdk-state/dl:/opt/sdk/dl" \
  openwrt-corosync bash /build/build.sh \
  2>&1 | tee output/build.log

tests/check-build-log.sh output/build.log
