#!/usr/bin/env bash
set -euo pipefail

SDK_DIR=/opt/sdk
OUTPUT_DIR=/build/output

mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*.apk "$OUTPUT_DIR"/sha256sums "$OUTPUT_DIR"/build-info.txt
cp -a /build/package/. "$SDK_DIR/package/"
cd "$SDK_DIR"

./scripts/feeds update base packages
./scripts/feeds install nspr nss

cat > .config <<'EOF'
CONFIG_TARGET_ath79=y
CONFIG_TARGET_ath79_generic=y
CONFIG_PACKAGE_libnss-qnetd=m
CONFIG_PACKAGE_corosync-qnetd=m
EOF

make defconfig
make package/nss-qnetd/compile V=s -j"$(nproc)"
make package/corosync-qnetd/compile V=s -j"$(nproc)"

find bin/packages -type f -name 'corosync-qnetd-*.apk' -exec cp {} "$OUTPUT_DIR"/ \;
test -n "$(find "$OUTPUT_DIR" -maxdepth 1 -name 'corosync-qnetd-*.apk' -print -quit)"
/build/tests/check-binaries.sh "$SDK_DIR" "$OUTPUT_DIR"
/build/tests/check-apk.sh "$SDK_DIR" "$OUTPUT_DIR"

git_commit=$(git -C /build rev-parse HEAD 2>/dev/null || echo unknown)
cat > "$OUTPUT_DIR/build-info.txt" <<EOF
Repository: H234598/corosync-qnetd-openwrt-mips
Git commit: $git_commit
OpenWrt: 25.12.5
SDK: openwrt-sdk-25.12.5-ath79-generic_gcc-14.3.0_musl.Linux-x86_64.tar.zst
Target: ath79
Subtarget: generic
Architecture: mips_24kc
Endianness: big endian
Compiler: GCC 14.3.0 / musl
NSS: 3.112 (build-time nss-qnetd)
NSPR: official OpenWrt nspr
qnetd: 3.0.4
Build date: $(date -u +%FT%TZ)
EOF
(cd "$OUTPUT_DIR" && sha256sum ./*.apk > sha256sums)
