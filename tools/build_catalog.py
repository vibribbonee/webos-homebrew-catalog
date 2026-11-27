#!/usr/bin/env python3
"""Rebuild repo.json from the newest GitHub release of each package.

For every package in packages.json, find the newest published release (and
pre-release, where allowed) that contains its IPK, then record the version,
download URL and SHA-256. Packages already in repo.json at the same URL keep
their hash, so unchanged IPKs are not downloaded again.

Usage: tools/build_catalog.py [--check]
  --check  exit 1 if repo.json would change, without writing it.
Set GITHUB_TOKEN to avoid the unauthenticated API rate limit.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com/repos/{repository}/releases?per_page=50"
RAW = "https://raw.githubusercontent.com/{repository}/main/{path}"
MAX_IPK_BYTES = 100 * 1024 * 1024


def request(url, accept="application/vnd.github+json"):
    headers = {"Accept": accept, "User-Agent": "webos-homebrew-catalog"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60)


def releases(repository):
    with request(API.format(repository=repository)) as response:
        return json.load(response)


def version_key(version):
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def newest_ipk(package, published):
    """The highest-version IPK for this package across its releases, as (version, url).

    A release can carry older IPKs too, so compare versions rather than taking
    the first match; a newer release wins a tie.
    """
    pattern = re.compile(package.get("asset") or re.escape(package["id"]) + r"_(?P<version>[0-9][0-9.]*)_all\.ipk")
    best = None
    for release in published:
        if release.get("draft") or (release.get("prerelease") and not package.get("prerelease")):
            continue
        for asset in release.get("assets", []):
            match = pattern.fullmatch(asset.get("name", ""))
            if not match:
                continue
            key = (version_key(match.group("version")), release.get("published_at") or "")
            if best is None or key > best[0]:
                best = (key, match.group("version"), asset["browser_download_url"])
    return None if best is None else (best[1], best[2])


def sha256(url):
    digest, size = hashlib.sha256(), 0
    with request(url, accept="application/octet-stream") as response:
        for chunk in iter(lambda: response.read(1 << 16), b""):
            size += len(chunk)
            if size > MAX_IPK_BYTES:
                raise ValueError(f"{url} is larger than expected")
            digest.update(chunk)
    return digest.hexdigest()


def build(config, current):
    known = {
        entry["manifest"]["ipkUrl"]: entry["manifest"]["ipkHash"]["sha256"]
        for entry in current.get("packages", [])
    }
    previous = {entry["id"]: entry for entry in current.get("packages", [])}
    cache, entries = {}, []
    for package in config["packages"]:
        repository = package["repository"]
        if repository not in cache:
            cache[repository] = releases(repository)
        found = newest_ipk(package, cache[repository])
        if found is None:
            if package["id"] in previous:  # Keep the last good entry rather than dropping the app.
                entries.append(previous[package["id"]])
            print(f"warning: no IPK release found for {package['id']}", file=sys.stderr)
            continue
        version, url = found
        icon = RAW.format(repository=repository, path=package["icon"])
        entries.append({
            "id": package["id"],
            "title": package["title"],
            "iconUri": icon,
            "manifest": {
                "id": package["id"],
                "title": package["title"],
                "version": version,
                "type": "web",
                "iconUri": icon,
                "sourceUrl": f"https://github.com/{repository}",
                "rootRequired": package.get("rootRequired", True),
                "ipkUrl": url,
                "ipkHash": {"sha256": known.get(url) or sha256(url)},
                "appDescription": package["description"],
            },
        })
    count = len(entries)
    return {"paging": {"page": 1, "count": count, "maxPage": 1, "itemsTotal": count}, "packages": entries}


def main():
    config = json.loads((ROOT / "packages.json").read_text())
    path = ROOT / "repo.json"
    current = json.loads(path.read_text()) if path.exists() else {}
    catalog = build(config, current)
    if catalog == current:
        print("repo.json is up to date")
        return 0
    if "--check" in sys.argv:
        print("repo.json is out of date")
        return 1
    path.write_text(json.dumps(catalog, indent=2) + "\n")
    for entry in catalog["packages"]:
        print(f"{entry['id']}: {entry['manifest']['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
