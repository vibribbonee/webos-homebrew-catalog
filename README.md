# webOS Homebrew catalog

Homebrew Channel repository for these rooted LG webOS apps:

- [Luma Home](https://github.com/vibribbonee/luma-home-webos) and Luma Camera Overlay
- [PanelComfort](https://github.com/vibribbonee/panelcomfort-webos)
- [ARC Guard](https://github.com/vibribbonee/arcguard)

## Add it to your TV

Open **Homebrew Channel → Settings → Add repository** and enter:

```
https://raw.githubusercontent.com/vibribbonee/webos-homebrew-catalog/main/repo.json
```

Homebrew Channel then offers updates whenever a new version is published.

## How it stays current

Every hour, a GitHub Action reads each app's newest release that contains its IPK, records the version and SHA-256, and commits `repo.json` when anything changed. Pre-releases are included for Luma Home. To add an app, add it to [`packages.json`](packages.json).

Run `tools/build_catalog.py` locally to rebuild the catalog, or `tools/build_catalog.py --check` to see whether it is current.

[MIT license](LICENSE).
