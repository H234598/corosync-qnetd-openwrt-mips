# Corosync QNetd for OpenWrt MIPS

Reproducible APK build for `corosync-qnetd 3.0.4` on TP-Link Archer C7 v2:

```text
Management: apd4.telacore.org / 192.168.40.8
QDevice VLAN endpoint: 192.168.62.11
OpenWrt 25.12.5, ath79/generic, mips_24kc, MIPS big-endian, musl
```

Router is QNetd arbitrator only. It is not Corosync member, Proxmox node, storage host, or VM host.
Init script binds QNetd only to `192.168.62.11`; port 5403 is not exposed on management address.

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

## Install on APD4

First inspect target. `apk --print-arch` may print `mips`; package architecture must still be `mips_24kc`.

```sh
ssh root@192.168.40.8 'cat /etc/openwrt_release; apk --print-arch; uname -a; df -h; free -h'
scp -O output/corosync-qnetd-*.apk root@192.168.40.8:/tmp/
ssh root@192.168.40.8 'apk add --allow-untrusted /tmp/corosync-qnetd-*.apk'
ssh root@192.168.40.8 'corosync-qnetd-certutil -i'
ssh root@192.168.40.8 '/etc/init.d/corosync-qnetd enable; /etc/init.d/corosync-qnetd start'
```

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

NSS database is persistent at `/etc/corosync/qnetd/nssdb`. Back it up before destructive tests:

```sh
tar czf /tmp/qnetd-nssdb-backup.tgz /etc/corosync/qnetd/nssdb
```

Archer C7 flash is limited. Never install SDK, sources, headers, object files, static libraries, or debug build outputs. Remove old APKs from `/tmp`.

## Firewall

Package makes no firewall changes. APD4 interface `QDevice` is in a dedicated
`input REJECT` firewall zone. Permit SSH/SFTP and TCP/5403 from QDevice subnet
`192.168.62.0/24`; never from WAN or another zone. PVE nodes communicate with
APD4 only through this subnet.

```sh
for port in 22 5403; do
  section="$(uci add firewall rule)"
  uci set "firewall.$section.name=Allow-QDevice-PVE-$port"
  uci set "firewall.$section.src=QDevice"
  uci add_list "firewall.$section.src_ip=192.168.62.0/24"
  uci set "firewall.$section.dest_port=$port"
  uci set "firewall.$section.proto=tcp"
  uci set "firewall.$section.target=ACCEPT"
done
uci commit firewall
/etc/init.d/firewall restart
```

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

Verify SSH and SFTP from a PVE node, then run:

```sh
pvecm qdevice setup 192.168.62.11
pvecm status
```

Before cluster creation, only transport preflight is possible: each PVE node must route directly from its `192.168.62.x` address to `192.168.62.11`; SSH/SFTP and TCP/5403 must connect. `pvecm qdevice setup`, votes, quorum-loss behavior, and reconnect validation require an existing cluster.

Use `pvecm qdevice setup 192.168.62.11 --force` only after failed setup. Expected result: QDevice has one vote. Reboot router and confirm service, TCP/5403, NSS DB, and QDevice reconnect. For daemon diagnostics run `corosync-qnetd -f`.

QDevice needs independent failure domain where possible. Common power/network failure shared by both PVE nodes and APD4 cannot be arbitrated away.

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
