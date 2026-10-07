#!/usr/bin/env python3
"""Reject common deployment data and credentials without printing their contents.

The default is the working-tree content of all Git-indexed paths, including new
staged files. --staged checks index contents instead; --directory checks an
extracted package or other directory. No history, refs, or Git logs are read.
This is a regression guard, not a complete secret or hostname detector.
"""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys


DOCUMENTATION_NETWORKS = (
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("2001:db8::/32"),
)
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?!\w|\.\d)", re.ASCII)
MASKED_IPV4 = re.compile(
    r"(?<![\w.])\d{1,3}\.\d{1,3}\.(?:\d{1,3}|[xX*?])\.[xX*?](?![\w.])",
    re.ASCII,
)
PRIVATE_IPV4_FRAGMENT = re.compile(
    r"(?<![\w.])(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|"
    r"192\.168|169\.254|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7]))"
    r"\.(?:\d{1,3}\.)?(?![\w.])",
    re.ASCII,
)
SHORT_IPV4_CIDR = re.compile(
    r"(?<![\w.])(?P<address>\d{1,3}(?:\.\d{1,3}){1,2})/"
    r"(?P<prefix>[0-9]|[12][0-9]|3[0-2])(?![\w.])",
    re.ASCII,
)
IPV6 = re.compile(
    r"(?<![\w:])(?:[a-fA-F0-9]{0,4}:){2,}[a-fA-F0-9:.]*"
    r"(?:%[\w.-]+)?(?![\w:])",
    re.ASCII,
)
PRIVATE_IPV6_FRAGMENT = re.compile(
    r"(?<![\w:])(?:[fF][dDcC][a-fA-F0-9]{2}|[fF][eE][89aAbB][a-fA-F0-9]):"
    r"(?![\w:])",
    re.ASCII,
)
TEXT_SIGNATURES = (
    ("key-or-certificate-material", re.compile(
        rb"-----BEGIN (?:[A-Z0-9 ]*PRIVATE KEY|[A-Z0-9 ]*CERTIFICATE(?: REQUEST)?)-----"
        rb"(?:[ \t\r\n]|\\n|\\r\\n)*"
        rb"(?:(?:Proc-Type|DEK-Info):[^\r\n]{0,200}\r?\n[ \t\r\n]*){0,2}"
        rb"[A-Za-z0-9+/]{32,}={0,2}"
    )),
    ("github-token", re.compile(
        rb"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{20,255}|"
        rb"github_pat_[A-Za-z0-9_]{22,255})(?![A-Za-z0-9_])"
    )),
    ("gitlab-token", re.compile(rb"(?<![A-Za-z0-9_])glpat-[A-Za-z0-9_-]{20,255}")),
    ("slack-token", re.compile(rb"(?<![A-Za-z0-9_])xox[baprs]-[A-Za-z0-9-]{20,255}")),
    ("aws-access-key", re.compile(rb"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])")),
    ("api-secret-key", re.compile(
        rb"(?<![A-Za-z0-9_])sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,255}"
    )),
    ("credential-in-url", re.compile(rb"(?:https?|ssh|ftp)://[^/\s:@]+:[^/@\s]+@")),
)
SENSITIVE_DIRECTORIES = re.compile(
    r"^(?:nssdb(?:[-_].*)?|secrets?|private|backups?|sdk-state|output|artifacts|"
    r"dist|build-logs|logs?|local-deploy|deploy-local|local-config|\.local)$", re.IGNORECASE
)
SENSITIVE_FILES = re.compile(
    r"(?:^\.env.*$|^(?:cert[89]|key[34]|secmod)\.db$|^pkcs11\.txt$|"
    r"^id_(?:rsa|dsa|ecdsa|ed25519)(?:\..*)?$|"
    r"\.(?:key|pem|p12|pfx|p7b|p7c|crt|cer|der|jks|keystore|"
    r"(?:db|sqlite[3]?)(?:-(?:wal|shm|journal))?|"
    r"log|bak|backup|old|orig|swp|swo|zip|tar|tgz|txz|tbz2?|gz|bz2|xz|zst|"
    r"7z|rar|apk|ipk|deb|rpm)$|(?:^|[._-])local(?:[._-].*)?$)",
    re.IGNORECASE,
)


def permitted_address(address):
    """Allow documentation, loopback, and harmless wildcard test sentinels."""
    if address.is_loopback or address.is_unspecified:
        return True
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return permitted_address(address.ipv4_mapped)
    return any(address.version == net.version and address in net
               for net in DOCUMENTATION_NETWORKS)


def ipv4_address(value):
    parts = value.split(".")
    if len(parts) != 4 or any(not part.isdigit() or int(part) > 255 for part in parts):
        raise ValueError("Invalid IPv4 address")
    return ipaddress.ip_address(".".join(str(int(part)) for part in parts))


def findings(path, data):
    found = set()
    relative = Path(path)
    if (any(SENSITIVE_DIRECTORIES.fullmatch(part) for part in relative.parts[:-1])
            or SENSITIVE_FILES.search(relative.name)):
        found.add((0, "sensitive-file-path"))

    def add(offset, category):
        found.add((data.count(b"\n", 0, offset) + 1, category))

    # Header strings occur in NSS code too; PEM detection requires payload bytes.
    for category, pattern in TEXT_SIGNATURES:
        for match in pattern.finditer(data):
            add(match.start(), category)

    # Latin-1 keeps byte offsets intact, including printable strings in ELF files.
    # Invalid candidate addresses (version triples, hashes, etc.) are ignored.
    content = data.decode("latin-1")
    for match in IPV4.finditer(content):
        try:
            address = ipv4_address(match.group())
        except ValueError:
            continue
        if not permitted_address(address):
            add(match.start(), "ipv4-address")
    for match in MASKED_IPV4.finditer(content):
        value = re.sub(r"[xX*?]", "0", match.group())
        try:
            address = ipv4_address(value)
        except ValueError:
            continue
        if not permitted_address(address):
            add(match.start(), "ipv4-fragment")
    for match in PRIVATE_IPV4_FRAGMENT.finditer(content):
        add(match.start(), "ipv4-fragment")
    for match in SHORT_IPV4_CIDR.finditer(content):
        parts = match.group("address").split(".")
        try:
            value = ipv4_address(".".join(parts + ["0"] * (4 - len(parts))))
            network = ipaddress.ip_network(f"{value}/{match.group('prefix')}", strict=False)
        except ValueError:
            continue
        if not (permitted_address(network.network_address)
                and permitted_address(network.broadcast_address)):
            add(match.start(), "ipv4-fragment")
    for match in IPV6.finditer(content):
        value = match.group().split("%", 1)[0].rstrip(".")
        # A prefix ending in a single colon can disclose the deployed subnet.
        if value.endswith(":") and not value.endswith("::"):
            value += ":"
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            continue
        if not permitted_address(address):
            add(match.start(), "ipv6-address-or-prefix")
    for match in PRIVATE_IPV6_FRAGMENT.finditer(content):
        add(match.start(), "ipv6-address-or-prefix")
    return sorted(found)


def git_command(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout


def indexed_files(root, staged):
    paths = sorted(set(git_command(root, "ls-files", "--cached", "-z").split(b"\0")) - {b""})
    for encoded in paths:
        name = os.fsdecode(encoded)
        if staged:
            yield name, git_command(root, "show", f":{name}")
        else:
            path = root / name
            if path.is_symlink():
                yield name, os.fsencode(os.readlink(path))
            elif path.exists():
                yield name, path.read_bytes()


def directory_files(root):
    # Never follow symlinks out of the package tree or read .git history.
    def walk_error(error):
        raise error

    for current, directories, files in os.walk(root, followlinks=False, onerror=walk_error):
        directories[:] = sorted(name for name in directories if name != ".git")
        links = [name for name in directories if (Path(current) / name).is_symlink()]
        directories[:] = [name for name in directories if name not in links]
        for name in sorted(files + links):
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                yield relative, os.fsencode(os.readlink(path))
            else:
                yield relative, path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--directory", type=Path, help="scan every file in an extracted directory")
    mode.add_argument("--repo", type=Path, help="Git working tree (default: this script's repository)")
    parser.add_argument("--staged", action="store_true", help="scan index contents instead of working files")
    args = parser.parse_args()
    if args.directory and args.staged:
        parser.error("--staged requires Git mode")
    if args.directory is not None and not args.directory.is_dir():
        parser.error("--directory must be a readable directory")

    try:
        if args.directory is not None:
            files = directory_files(args.directory)
        else:
            root = args.repo or Path(__file__).resolve().parent.parent
            root = Path(os.fsdecode(git_command(root, "rev-parse", "--show-toplevel")).rstrip("\n"))
            files = indexed_files(root, args.staged)
        scanned = 0
        failed = False
        for path, data in files:
            scanned += 1
            for line, category in findings(path, data):
                # JSON escaping also prevents hostile filenames from injecting log lines.
                print(json.dumps({"path": path, "line": line, "category": category},
                                 ensure_ascii=True))
                failed = True
    except (OSError, subprocess.CalledProcessError):
        print("Public-content check could not read all requested files.", file=sys.stderr)
        return 2
    if not scanned:
        print("Public-content check refused an empty input set.", file=sys.stderr)
        return 2
    if failed:
        print(f"Public-content check failed ({scanned} files scanned); values withheld.", file=sys.stderr)
        return 1
    print(f"Public-content check passed ({scanned} files scanned).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
