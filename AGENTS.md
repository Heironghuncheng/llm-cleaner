# Cleaner

Audit and clean leftover software configurations on Windows.
Scope: `%USERPROFILE%` only (home + AppData/Roaming + AppData/Local + AppData/LocalLow).
`C:\no_super` and `D:\game` are reference indices only, never cleaned.

Run all commands from `~/Project/cleaner` using `uv run python -m src <command>`.

## Commands

| Command | Purpose |
|---------|---------|
| `uv run python -m src scan` | Full scan + diff (auto-called by audit) |
| `uv run python -m src scan <key>` | Partial refresh by config key |
| `uv run python -m src deep <name\|file> [name...]` | Deep scan one or more items → scan/partial/ |
| `uv run python -m src deep <name> --depth N` | Deep scan with override depth (-1 = unlimited) |
| `uv run python -m src match <name\|file>` | Fuzzy match single item or batch from file |
| `uv run python -m src verify <report>` | Verify report: diff 模式比对 diff 数量，full 模式全量匹配 |
| `uv run python -m src remove <path>` | Delete stale item |

## Skills

| Skill | Trigger | Flow |
|-------|---------|------|
| `cleaner-first-use` | "首次使用" / "first use" / "setup" | explain scope → review defaults → ask stepwise config questions → validate first scan |
| `cleaner-audit` | "审计" / "audit" | scan → classify → report → ask clean |
| `cleaner-clean` | invoked by audit | read report → confirm → delete |
| `cleaner-config` | "配置" / "config" | edit config.json + facts.md |

All prompts and reports are bilingual (中/英).

Tracked source copies of the Cleaner-specific skills live under `skill-sources/cleaner/`. Local `.agents/skills/` and `.claude/skills/` installs are not part of the published repository state.

## Config (config.json)

All scan targets are configured in `config.json`. No hardcoded directories.

| Field | Type | Description |
|-------|------|-------------|
| `scan_dirs` | `{key: path}` | Directories to scan. Empty `""` = home dir. Relative to `%USERPROFILE%`. |
| `scan_depths` | `{key: int}` | Depth per directory. `default` key is fallback for unspecified keys. |
| `deep_scan_depth` | int | Default depth for `deep` command. `-1` = unlimited. Overridable with `--depth`. |
| `stale_months` | int | Months threshold for `*` stale marker. |
| `manual_dirs` | [str] | Reference dirs (never cleaned). |
| `package_managers` | [str] | Which PMs to query. |

Output filename: key `/` → `_` + `.txt`. E.g. `appdata/roaming` → `scan/appdata_roaming.txt`.

Depth lookup: `scan_depths.get(key, scan_depths.get("default", 1))`.

## Scan output

| File | Content |
|------|---------|
| `scan/packages.txt` | All package manager entries |
| `scan/manual-index.txt` | Subdirectory names from manual dirs |
| `scan/<key>.txt` | Each directory from scan_dirs (items tagged `*` if old) |
| `scan/diff.txt` | Changes since last scan |
| `scan/partial/<name>.txt` | Deep scan for specific item |
| `report-YYYY-MM-DD.md` | CC classification report |

## Report actions

| Action | Meaning |
|--------|---------|
| `delete` | Stale leftover, safe to remove |
| `remind` | Stale but software still active, note for future |
| `keep` | Active software or system |
| `unknown` | Investigated but cannot determine source |

## facts.md format (YAML)

```yaml
active:
  - path: .codex/
    reason: scoop codex installed
no_clean:
  - .ssh
  - AppData/Local/Microsoft
stale:
  - path: AppData/Local/BleachBit
    reason: uninstalled
```

User-maintained soft memory. Only updated by user or on explicit request.

## Reset

When user says "reset" or "重置", delete all generated files:
- `scan/` directory (all scan output + partial results)
- `report-*.md` files (all audit reports)

Do NOT delete: source code, config.json, facts.md, skills, AGENTS.md, .Codex/
