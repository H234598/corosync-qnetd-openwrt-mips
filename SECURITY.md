---
title: Publication and configuration security
aliases:
  - QNetd publication guidelines
tags:
  - security/opsec
  - openwrt
  - corosync
type: security-policy
status: maintained
date: 2026-10-06
created: 2026-10-06
updates:
  - date: 2026-10-06
    change: Document local configuration and publication checks.
---

# Publication and configuration security

This is a public package repository. Published content should explain how to
build and configure the software without describing a particular deployment.

## Keep deployment data local

Keep real addresses, DNS names, cluster and device inventories, certificate
databases, private keys, environment files, backups, and raw diagnostics outside
Git. Set the listener in `/etc/config/corosync-qnetd` on the target device. The
packaged configuration contains no deployment address.

Use reserved documentation addresses and domains in examples. Documentation
must clearly identify them as examples. Build targets, dependency versions,
checksums, and public upstream URLs are legitimate package metadata; do not
present them as facts about a live environment.

## Check before publishing

```sh
python3 scripts/check-public-content.py
python3 scripts/check-public-content.py --staged
python3 tests/check-public-content.py
bash tests/check-init.sh
bash tests/check-upstream-update.sh
git diff --cached --check
```

The first command inspects the working content of tracked files, including new
staged paths. The second inspects the exact staged content. Explicitly stage
intended files and review that diff before committing. A check in Actions runs
after a GitHub push; it cannot undo an exposure already caused by that push.

The checker reports a path, line, and category without displaying the matched
value. It detects selected network-address and credential patterns and sensitive
file types. It cannot reliably infer whether an arbitrary hostname, person's
name, topology description, screenshot, encoded payload, or binary is private.
Manual review is still required. Ignore rules prevent accidental staging but
do not protect already tracked files or remove historical copies.

The package checks compare the installed init script and UCI configuration with
the sources, exercise the configuration boundary, and scan the extracted APK.
Publication workflows upload only the package, checksums, and generic build
metadata. Review Actions console output and release notes separately.

## Handling a previous disclosure

Do not copy sensitive values into a public issue, pull request, commit message,
release note, or regression fixture. Keep exact matching lists outside the
repository. If a credential was exposed, revoke or rotate it; deleting its text
does not invalidate it.

Correcting current files does not remove old commits, tags, release assets,
Actions artifacts, caches, or external clones. Identify each affected surface,
coordinate any history rewrite, and verify its result. Avoid public backup
branches or tags containing the original data. Old clones must not merge the
discarded history back into a cleaned repository.

For exposure reports, use an established private channel to the maintainer. Do
not place the actual value in a public report. A neutral file path and a request
for private follow-up are sufficient for an initial public notice.

## References

- [GitHub: removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [GitHub: forks and their shared network](https://docs.github.com/en/pull-requests/reference/forks)
- [RFC 5737: IPv4 address blocks reserved for documentation](https://www.rfc-editor.org/rfc/rfc5737)
- [RFC 3849: IPv6 address prefix reserved for documentation](https://www.rfc-editor.org/rfc/rfc3849)
