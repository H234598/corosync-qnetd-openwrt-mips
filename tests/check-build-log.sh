#!/usr/bin/env bash
set -euo pipefail

log=${1:?build log required}
grep -Fq 'OS_TEST=mips' "$log"
grep -Fq 'CPU_ARCH=mips' "$log"
grep -Fq 'OS_ARCH=Linux' "$log"
grep -Fq 'OS_TARGET=Linux' "$log"
grep -Fq 'NSS_USE_64=0' "$log"
grep -Fq '/nss-qnetd-3.112/' "$log"
grep -Eq 'mips-openwrt-linux-musl-(gcc|g\+\+)' "$log"
if grep -Fq 'ar cr cr' "$log"; then
	exit 1
fi
if grep -Eqi 'aarch64|mipsel' "$log"; then
	exit 1
fi
