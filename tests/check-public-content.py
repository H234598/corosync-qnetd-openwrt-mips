#!/usr/bin/env python3
"""Exercise real CLI modes with temporary data; no real credentials are used."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-public-content.py"


def dotted(*parts):
    return ".".join(str(part) for part in parts)


class PublicContentChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)

    def scan(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def directory_scan(self):
        return self.scan("--directory", str(self.root))

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.root), *args], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_safe_documentation_versions_upstreams_and_wildcards(self):
        self.write("example.txt", "\n".join((
            "192.0.2.10 198.51.100.8 203.0.113.7 2001:db8::42",
            "127.0.0.1 ::1 0.0.0.0 :: [::] ::ffff:192.0.2.10",
            "192.0.2.x 203.0.113/24",
            "3.0.4 25.12.5 gcc-14.3.0 v1.2.3.4",
            "https://downloads.openwrt.org/releases/25.12.5/",
            "https://github.com/corosync/corosync-qdevice",
            "e7d45be10e63cc209d2109829e61720959093c87a88c75241051e2eabebf4ec0",
            "NSS format marker: -----BEGIN " + "CERTIFICATE-----",
        )))
        result = self.directory_scan()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_non_documentation_networks_fragments_and_binary_strings(self):
        candidates = (
            dotted(10, 23, 42, 1), dotted(172, 20, 0, 1),
            dotted(192, 168, 42, 1), dotted(100, 80, 1, 2),
            dotted(8, 8, 4, 4), dotted(192, 168, 42, "*"),
            dotted(192, 168, "x", "x"), dotted(10, 23, ""),
            dotted(172, 20, ""), dotted(192, 168, 42) + "/24",
            ":".join(("fdab", "1234", "", "42")),
            ":".join(("fe80", "", "42%eth0")),
            ":".join(("2001", "4860", "4860", "", "8888")),
            ":".join(("fdab", "1234", "")),
            "fdab" + ":", "::ffff:" + dotted(10, 23, 42, 1),
        )
        for candidate in candidates:
            with self.subTest(candidate_index=candidates.index(candidate)):
                self.write("fixture.txt", "first line\naddress=" + candidate + "\n")
                result = self.directory_scan()
                self.assertEqual(result.returncode, 1)
                records = [json.loads(line) for line in result.stdout.splitlines()]
                self.assertTrue(any(record["line"] == 2 for record in records))
                self.assertNotIn(candidate, result.stdout + result.stderr)
        for candidate in (candidates[0], candidates[10]):
            self.write("fixture.txt", "Address: " + candidate + ".\n")
            self.assertEqual(self.directory_scan().returncode, 1)
        self.write("fixture.txt", b"\x7fELF\x00embedded=" + candidates[0].encode() + b"\x00")
        self.assertEqual(self.directory_scan().returncode, 1)

    def test_synthetic_secret_signatures_do_not_echo_values(self):
        secrets = (
            "gh" + "p_" + "a" * 36,
            "github_" + "pat_" + "b" * 40,
            "gl" + "pat-" + "c" * 24,
            "xox" + "b-" + "d" * 24,
            "AK" + "IA" + "E" * 16,
            "sk" + "-proj-" + "f" * 32,
            "-----BEGIN " + "PRIVATE KEY-----\n" + "Z" * 64,
            "-----BEGIN " + "CERTIFICATE-----\n" + "Z" * 64,
            "-----BEGIN " + "PRIVATE KEY-----\\n" + "Z" * 64,
            "-----BEGIN " + "RSA PRIVATE KEY-----\nProc-Type: 4,ENCRYPTED\n"
            + "DEK-Info: AES-256-CBC,synthetic-fixture\n\n" + "Z" * 64,
            "https://" + "fixture-user:fixture-password@" + "example.org/",
        )
        for index, secret in enumerate(secrets):
            with self.subTest(signature=index):
                self.write("fixture.txt", secret)
                result = self.directory_scan()
                self.assertEqual(result.returncode, 1)
                self.assertNotIn(secret, result.stdout + result.stderr)
                self.assertTrue(all(set(json.loads(line)) == {"path", "line", "category"}
                                    for line in result.stdout.splitlines()))

    def test_sensitive_paths(self):
        paths = (
            "nested/nssdb-seed/contents", "etc/corosync/qnetd/nssdb/contents",
            "nested/cert9.db", "nested/key4.db", "nested/secmod.db", "pkcs11.txt",
            ".env", "nested/.env.production", "ca.crt", "client.pem", "private.key",
            "client.p12", "client.pfx", "client.p7b", "client.cer", "store.sqlite3",
            "key4.db-wal", "cert9.db-shm", "store.sqlite3-journal",
            "backup.tar.gz", "artifact.apk", "build.log", "config.bak", "config.local",
            "output/file", "artifacts/file", "local-deploy/config",
        )
        for index, path in enumerate(paths):
            with self.subTest(path_index=index):
                self.write(path, "synthetic fixture")
                result = self.directory_scan()
                self.assertEqual(result.returncode, 1)
                self.assertIn('"category": "sensitive-file-path"', result.stdout)
                (self.root / path).unlink()

    def test_git_ignores_local_material_but_force_added_material_is_checked(self):
        self.git("init", "-q")
        self.write(".gitignore", (SCRIPT.parents[1] / ".gitignore").read_bytes())
        paths = (
            "package/corosync-qnetd/files/nssdb-seed/cert9.db", "nested/nssdb/key4.db",
            "local-deploy/config", "output/package.apk", "private.key", "key4.db-wal",
            ".env.production", "logs/build.log", "config.local", "backup.tar.gz",
        )
        result = subprocess.run(
            ["git", "-C", str(self.root), "check-ignore", "--no-index", "--stdin"],
            input="\n".join(paths) + "\n", stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, check=True,
        )
        self.assertEqual(result.stdout.splitlines(), list(paths))
        self.write(".env.production", "synthetic fixture")
        self.git("add", "--force", ".env.production")
        self.assertEqual(self.scan("--repo", str(self.root)).returncode, 1)

    def test_git_tracked_index_additions_and_untracked_files(self):
        self.git("init", "-q")
        self.write("public.txt", "192.0.2.1\n")
        self.git("add", "public.txt")
        self.write("untracked.txt", dotted(10, 23, 42, 1))
        self.assertEqual(self.scan("--repo", str(self.root)).returncode, 0)
        self.write("new-file.txt", dotted(10, 23, 42, 1))
        self.git("add", "new-file.txt")
        self.assertEqual(self.scan("--repo", str(self.root)).returncode, 1)
        self.write("new-file.txt", "192.0.2.1\n")
        self.assertEqual(self.scan("--repo", str(self.root)).returncode, 0)
        self.assertEqual(self.scan("--repo", str(self.root), "--staged").returncode, 1)
        self.git("add", "new-file.txt")
        self.assertEqual(self.scan("--repo", str(self.root), "--staged").returncode, 0)

    def test_directory_scan_does_not_follow_symlinks_or_git_history(self):
        self.write("public.txt", "safe fixture\n")
        self.write(".git/logs/HEAD", dotted(10, 23, 42, 1))
        (self.root / "broken-link").symlink_to("nonexistent-target")
        self.assertEqual(self.directory_scan().returncode, 0)

    def test_fail_closed_for_missing_and_empty_inputs(self):
        self.assertEqual(self.scan("--directory", str(self.root / "missing")).returncode, 2)
        self.assertEqual(self.directory_scan().returncode, 2)
        self.assertEqual(self.scan("--repo", str(self.root)).returncode, 2)


if __name__ == "__main__":
    unittest.main()
