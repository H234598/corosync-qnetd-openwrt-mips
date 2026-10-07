---
title: Corosync QNetd for OpenWrt MIPS
aliases:
  - OpenWrt MIPS QNetd package
tags:
  - openwrt
  - corosync
  - qnetd
  - security/opsec
type: documentation
status: maintained
date: 2026-10-06
created: 2026-09-11
updates:
  - date: 2026-10-06
    change: Separate deployment configuration from public build sources.
---

# Corosync QNetd for OpenWrt MIPS

APK build for `corosync-qnetd` on OpenWrt `ath79/generic`, `mips_24kc`,
MIPS big-endian with musl. Hardware compatibility depends on the target and ABI;
verify both on the device before installing.

QNetd is an external quorum arbitrator, not a Corosync member or a virtualization
host. This repository contains generic build instructions and example addresses
only. Keep real hostnames, network addresses, cluster inventories, firewall
configuration, certificates, and deployment logs outside the repository.

The service reads its IPv4 bind address from local UCI configuration. It refuses to
start until an address is configured. The package never creates firewall rules.
See [local configuration](#local-configuration) and the
[publication guidelines](SECURITY.md).

## Build

Requires Podman or Docker on Linux x86_64. `run-build.sh` uses Docker when present,
otherwise Podman.

```sh
podman build -t openwrt-corosync .
bash run-build.sh
```

Docker verifies official SDK SHA256 before extraction:

```text
openwrt-sdk-25.12.5-ath79-generic_gcc-14.3.0_musl.Linux-x86_64.tar.zst
bc4307ae2065c0c0b7c84627356e9f3d368a5a803c81552fcb77aa034a843f5a
```

`output/` contains `corosync-qnetd-*.apk`, `build.log`, `build-info.txt`, and `sha256sums`. Build checks reject MIPSel, ARM, x86, glibc, `ar cr cr`, wrong APK architecture, undeclared package dependencies, and static/build artifacts.

Clean build: remove `sdk-state/` before `bash run-build.sh`. Do not reuse cache after target or compiler changes.

## Automatic upstream releases

GitHub Actions checks the latest stable `corosync/corosync-qdevice` release daily
and can also be started manually. For a newer semantic version it downloads the
exact tag archive, calculates `PKG_HASH`, resets `PKG_RELEASE` to 1, and runs the
same SDK build and checks used locally. Only a successful build is committed,
tagged as `v<upstream-version>-r<package-release>`, and published with APK, checksum, and build
metadata. Drafts, prereleases, malformed versions, downgrades, failed builds,
and branch races produce no release. A new upstream version resets the package
revision to 1; a package-only change retains its own revision. This lets changes
to configuration and packaging be released without pretending that upstream code
has changed.

If a run stops after pushing its tag but before creating the release, rerunning
the workflow can rebuild and publish the missing release while `master` still
matches that tag. If the branch has moved, it fails closed and requires review.
Upstream source changes
that need patches or a newer NSS/OpenWrt toolchain fail closed and require a
reviewed repository change.

## Install

First inspect the target. `apk --print-arch` may print `mips`; the package
architecture must still be `mips_24kc`. All addresses below belong to reserved
example ranges. Replace them locally; do not commit your real values.

**Upgrading from r1:** schedule the change while the cluster is healthy and can
tolerate a temporary loss of the arbitrator. Package installation can stop and
start the service automatically. Before running `apk add`, create and set the
local UCI configuration using the commands in [local configuration](#local-configuration).
After installation, verify that your settings were retained and check the
listener and cluster reconnection. If the address is absent, the new service
stays stopped until it is configured. The NSS database does not need to be
reinitialized for this upgrade.

```sh
# On the build/client machine; example value only.
ROUTER_HOST=192.0.2.10
ssh "root@$ROUTER_HOST" 'cat /etc/openwrt_release; apk --print-arch; uname -a; df -h; free -h'
scp -O output/corosync-qnetd-*.apk "root@$ROUTER_HOST:/tmp/"
ssh "root@$ROUTER_HOST" 'apk add --allow-untrusted /tmp/corosync-qnetd-*.apk'
```

### Local configuration

Run these commands on the router, using the specific local IPv4 address that the
cluster should reach. The address must already exist on the router.

```sh
# Example only: replace locally with the intended service address.
test -e /etc/config/corosync-qnetd || touch /etc/config/corosync-qnetd
uci set corosync-qnetd.main=qnetd
uci set corosync-qnetd.main.listen_address='192.0.2.10'
uci commit corosync-qnetd
# Fresh installation only: do not reinitialize an existing certificate database.
corosync-qnetd-certutil -i
/etc/init.d/corosync-qnetd enable
/etc/init.d/corosync-qnetd start
```

`/etc/config/corosync-qnetd` is registered as a package configuration file so that
local settings are preserved during upgrades. It ships with an empty address.
The init script accepts only canonical dotted-decimal IPv4 addresses and rejects
the unspecified address. Hostnames, IPv6, shorthand and octal forms are refused;
the previous package also used an IPv4 listener. After changing the configuration,
restart the service and verify its listening address.

The address formerly built into r1 is no longer part of the package. There is
no automatic migration from the old init script. Existing NSS databases are not
changed by this configuration migration. For an upgrade, run only the UCI
configuration commands before package installation and keep the existing NSS
database; then check `/etc/config/corosync-qnetd` again after installation.

Do not use `--nodeps` or `--no-deps`. APK resolves official OpenWrt runtime packages: `libnss`, `nspr`, `nss-utils`, `openssl-util`, `bash`, `coreutils-chown`, `coreutils-stat`, `coreutils-sha1sum`, `procps-ng-ps`, `procps-ng-w`, and `openssh-sftp-server`.

| Package | Used for | Required by | Source |
| --- | --- | --- | --- |
| `libnss` | TLS, certificate DB, PKCS#11 | `corosync-qnetd` | official packages feed, runtime |
| `nspr` | NSS portability layer | NSS and QNetd | official packages feed, build/runtime |
| `nss-utils` | `certutil`, `pk12util` | certificate setup | official packages feed, runtime |
| `openssl-util` | certificate conversion/checks | certificate setup | official base feed, runtime |
| `bash` | upstream `corosync-qnetd-certutil` | certificate setup | official packages feed, runtime |
| `coreutils-chown`, `coreutils-stat`, `coreutils-sha1sum` | upstream script commands | certificate setup | official packages feed, runtime |
| `procps-ng-ps`, `procps-ng-w` | full `ps` and `w`; BusyBox variants are insufficient | certificate setup | official packages feed, runtime |
| `openssh-sftp-server` | Proxmox certificate transfer | `pvecm qdevice setup` | official base feed, runtime |

Minimal NSS 3.112 under `package/nss-qnetd` is build-only. Its six shared libraries and headers live in isolated SDK staging path; none enter QNetd APK. Runtime always uses official `libnss`.

NSS database is persistent at `/etc/corosync/qnetd/nssdb`. Back it up before destructive tests and keep the backup private:

```sh
umask 077
tar czf /tmp/qnetd-nssdb-backup.tgz /etc/corosync/qnetd/nssdb
```

Embedded router flash may be limited. Never install SDK, sources, headers, object files, static libraries, or debug build outputs. Remove old APKs from `/tmp`.

## Firewall

Use an appropriate firewall zone and permit only the required cluster nodes to
reach the service. Review access to TCP/5403 and, where needed for certificate
setup, SSH/SFTP. Do not expose the arbitrator to the WAN. The following example
assumes that a dedicated zone with a rejecting input policy already exists; it
does not create the zone, attach interfaces, or describe any deployed network.

```sh
# On the router; replace all example values locally.
QDEVICE_ZONE=qdevice_example
NODE_ONE=192.0.2.21
NODE_TWO=192.0.2.22
for port in 22 5403; do
  section="$(uci add firewall rule)"
  uci set "firewall.$section.name=Allow-QDevice-$port"
  uci set "firewall.$section.src=$QDEVICE_ZONE"
  uci add_list "firewall.$section.src_ip=$NODE_ONE"
  uci add_list "firewall.$section.src_ip=$NODE_TWO"
  uci set "firewall.$section.dest_port=$port"
  uci set "firewall.$section.proto=tcp"
  uci set "firewall.$section.target=ACCEPT"
done
uci commit firewall
/etc/init.d/firewall restart
```

These commands add rules on every execution. Inspect existing rules before
running them again and retain an independent management path while testing.

## Verify and Proxmox

```sh
/etc/init.d/corosync-qnetd status
netstat -tlnp | grep 5403
corosync-qnetd-tool -l
ldd /usr/sbin/corosync-qnetd
certutil -H
pk12util -h
openssl version
```

Inspect diagnostic output locally; it can reveal client identities and
addresses. Verify the actual bound address and SSH/SFTP connectivity from each
intended node before configuring a cluster. On an existing cluster, run:

```sh
# On a Proxmox node; replace the documentation address locally.
pvecm qdevice setup 192.0.2.10
pvecm status
```

Transport checks alone do not prove quorum behavior. Validate votes,
quorum-loss behavior, and reconnection on the existing cluster in a planned test.
A failed setup requires diagnosing the failure before considering a forced retry.
When testing a router reboot, check the service, listening socket, persistent NSS
database, and cluster reconnection afterward. Foreground daemon diagnostics also
need the intended explicit bind address; do not start an extra wildcard listener.

Place QNetd in an independent failure domain where practical. A shared power or
network failure affecting the arbitrator and both cluster nodes cannot be
resolved by quorum arbitration alone.

## Update, rollback, removal

Record flash use before and after install:

```sh
df -h /overlay
du -sh /etc/corosync /usr/sbin/corosync-qnetd* 2>/dev/null
```

For update, back up NSS DB, install newer APK, restart service, then repeat all checks. Keep previous APK until QDevice reconnects. For rollback, install previous local APK and restart; `--force-overwrite` is not a downgrade switch.

Before removal, run `pvecm qdevice remove` on Proxmox. Then:

```sh
/etc/init.d/corosync-qnetd stop
/etc/init.d/corosync-qnetd disable
apk del corosync-qnetd
```

Remove `/etc/corosync/qnetd` only after confirming its certificates and DB are no longer needed. Shared runtime dependencies may belong to other packages; do not delete them manually.

## Publication checks

Run the local checks before committing or publishing:

```sh
python3 scripts/check-public-content.py
python3 tests/check-public-content.py
bash tests/check-init.sh
bash tests/check-upstream-update.sh
```

The content check scans Git-tracked files, including newly staged files, and the
package check also scans the extracted APK. It reports locations and categories
without echoing matched values. It is a regression guard, not a guarantee that
all confidential information can be recognized automatically. Review prose,
release notes, hostnames, screenshots, and logs manually as well.

CI publishes only the APK, checksum, and generic build metadata; raw build logs
stay out of downloadable artifact bundles. Actions job logs remain a separate
publication surface and require the same care. Temporary artifacts expire after
seven days; releases have a separate lifetime.

See [SECURITY.md](SECURITY.md) for handling local secrets and previous disclosures.
