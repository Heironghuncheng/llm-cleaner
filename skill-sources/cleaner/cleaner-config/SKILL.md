---
name: cleaner-config
description: Use when the user wants to change Cleaner scan scope, depth, package-manager sources, or update the facts memory file.
---

# Cleaner Config

## Critical Guidelines

- You MUST ask user before modifying `manual_dirs` or `package_managers`.
- You MUST ask user before writing to `facts.md`.
- You MUST validate config with a test scan after changes.

## When to Use

Trigger: "配置" / "config" / "add scan dir" / "change depth" / "update facts"

## How to Use

### config.json

```json
{
  "manual_dirs": ["C:\\no_super", "D:\\game"],
  "stale_months": 1,
  "deep_scan_depth": 3,
  "package_managers": ["scoop", "winget", "choco", "mise", "uv_tool"],
  "scan_dirs": {
    "home": "",
    "appdata/roaming": "AppData/Roaming"
  },
  "scan_depths": {
    "default": 1,
    "home": 1,
    "appdata/roaming": 1
  }
}
```

### Field reference

| Field | Type | Description |
|-------|------|-------------|
| `scan_dirs` | `{key: path}` | Scan targets. `""` = home dir. Relative to `%USERPROFILE%`. |
| `scan_depths` | `{key: int}` | Depth per key. `default` is fallback. `-1` = unlimited. |
| `deep_scan_depth` | int | Default depth for `deep` command. Overridable with `--depth`. |
| `stale_months` | int | Threshold for `*` stale marker. |
| `manual_dirs` | [str] | Reference dirs (never cleaned). |
| `package_managers` | [str] | PMs to query. |

Depth lookup: `scan_depths.get(key, scan_depths.get("default", 1))`

Output filename: replace `/` with `_` in key, append `.txt`.

### Common operations

**Add directory:**
```json
"scan_dirs": { ..., "chrome/profile": "AppData/Local/Google/Chrome/User Data" },
"scan_depths": { ..., "chrome/profile": 1 }
```
Run `uv run python -m src scan chrome/profile` to test.

**Remove directory:** Delete key from `scan_dirs` and `scan_depths`.

**Change depth:** Update `scan_depths` value. `-1` = unlimited.

### Validation

```bash
uv run python -m src scan <key>   # test one
uv run python -m src scan          # test all
```

### facts.md format

```yaml
active:
  - path: .codex/
    reason: scoop codex installed
no_clean:
  - .ssh
stale:
  - path: AppData/Local/BleachBit
    reason: uninstalled 2025-10
```

| Section | Effect on audit |
|---------|-----------------|
| `active` | Hint toward `keep`; still verify against current scan results |
| `no_clean` | User preference hint toward `keep`; still include the item in the report |
| `stale` | Hint toward `remind` or deeper investigation; not an automatic `delete` |

Rules: paths relative to `%USERPROFILE%`, `facts.md` is prompt memory rather than ground truth, entries still need to be represented in the audit report, CC asks before writing, remove entries when situation changes.

## Quick Reference

| Action | Trigger |
|--------|---------|
| Add to `active` | User says "this is active" |
| Add to `no_clean` | User says "never clean this" |
| Add to `stale` | User confirms something is stale |
| Remove entry | Situation changed |
