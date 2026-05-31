---
name: cleaner-audit
description: Use when user asks to audit leftover software files, stale configs, or Windows cleanup candidates in this Cleaner project.
---

# Cleaner Audit

## Classification Rules

Work through this table top-to-bottom for each item. First match wins.

| # | Condition | Action | Key evidence |
|---|-----------|--------|-------------|
| 1 | **System item**: Windows directory / Junction / Registry hive / `NTUSER.*` / `AppData` / `Desktop` / `Documents` / `「开始」菜单` ... | `keep` | Part of Windows, not third-party software |
| 2 | **User data**: directory/file the user deliberately created — project source code, documents, personal scripts. The user would recognize it as their own work. NOT: software workspaces (Go, Node, Rust toolchains), NOT: unrecognized data files. | `keep` | Contains user's own work; user can identify it |
| 3 | **Empty directory** (no files, no subdirs, or only a `.log` file) | `delete` | `deep` scan shows nothing inside |
| 4 | **Pure cache / temp** (see list below) | `delete` | Regenerated on next use; no user settings |
| 5 | Software identified, **confirmed uninstalled** (not in any PM, no recent `.exe`) | `delete` | Source known, software gone; residual config only |
| 6 | **`*` stale marker** present (all content older than `stale_months`) — rules #1–#5 take precedence | `remind` | Item is old; user should decide whether to keep or delete |
| 7 | Software identified, **installed and active** (found in PM or manual index, no `*`) | `keep` | Software in active use |
| 8 | **Cannot identify** which software created this after deep scan + web search, and the item is **not** being handled by the stale `*` rule | `unknown` | Truly untraceable; never `delete` |

### Cache / temp list (rule #4)

Always safe to delete — regenerated on next use:

- `*-updater`, `*-cache`, `*_cache`, `*-temp`, `*_temp`
- `Cache`, `Temp`, `CrashDumps`, `D3DSCache`, `SquirrelTemp`
- `node-gyp`, `npm-cache`, `pnpm-cache`, `pnpm-state`, `go-build`, `hugo_cache`
- `Temporary Internet Files`, `IconCache.db`, `GDIPFONTCACHEV1.DAT`

### Stale marker `*`

`*` means the item's newest content is older than `stale_months`. Default action: `remind` (rule #6).

- Rules #1–#5 are checked first — a stale system dir is still `keep`, a stale empty dir is still `delete`
- `*` + confirmed uninstalled → `delete` (rule #5 overrides #6)
- `*` + installed and active → `remind` (software may be abandoned)
- `*` + can't determine software → still `remind` (old and unidentified, so flag it for user review instead of guessing)
- `unknown` is for non-stale items that remain untraceable after investigation
- Deep scan may reveal newer nested content → re-evaluate `*` status

### Evidence format

Each report row's Evidence must follow one of these patterns:

| Classification basis | Evidence format | Example |
|---------------------|----------------|---------|
| System item | `Windows <component>` | `Windows system directory` |
| User data | `User project: <description>` | `User project: Python source files` |
| PM match | `<pm>: <package> [活跃 / active]` | `winget: valve.steam 活跃` |
| Manual index | `manual: <name> 活跃` | `manual: Battle.net 活跃` |
| Stale (`*`) | `Stale since YYYY-MM-DD, <detail>` | `Stale since 2025-08, software still installed` |
| Stale + uninstalled | `Not in PM, stale since YYYY-MM-DD` | `Not in PM, stale since 2025-09-25` |
| Cache/temp | `Cache, regenerated on use` | `Cache, regenerated on use` |
| Empty | `Empty directory` | `Empty directory` |
| Web search | `Web: <source>, <status>` | `Web: NVIDIA Ansel, uninstalled` |
| Unknown | `Cannot determine source` | `Cannot determine source` |

## Critical Guidelines

- You MUST always run a full scan before classification — no exceptions.
- You MUST verify the report with `src verify` before presenting.
- You MUST classify every item — no item left unaccounted for.
- You MUST web search unknown items — try every tool before giving up.
- You MUST present results bilingually (中/英).
- `facts.md` is prompt memory, not ground truth. Use it as a hint when classifying, but still verify against scan output and still account for every item in the report.
- `facts.md` `no_clean` entries usually classify as `keep` unless the user explicitly overrides them. `stale` entries are investigation/reminder hints, not automatic `delete`.
- **Recent dates ≠ keep.** A file modified last week is still residual if its software is uninstalled. Always check the PM before deciding. `Recent 260417` with no PM match → `delete` or `remind`, not `keep`.
- **User data must be user-created.** Software workspaces (Go, Rust, Node) are NOT user data — they're software artifacts. If the software is gone, the workspace is residual. If the user doesn't recognize the file, it's not user data → `unknown`.

## When to Use

Trigger: "审计" / "audit" / "check leftovers" / "find stale configs"

## How to Use

All commands run from `~/Project/cleaner`.

### Step 1: Scan

```bash
uv run python -m src scan
```

Scan output format per item: `name  type  [size]  YYMMDD  [*]`
- `*` = stale (older than `stale_months`)
- Size only for files, units: K/M/G/T
- Date is compact: `260515` = 2026-05-15

### Step 2: Review diff & scope

Read `scan/diff.txt` if it exists. Diff markers:
- `"No changes."` — identical to last scan
- `+ name` — new item
- `- name` — removed item
- `~ name` — line changed (e.g. gained `*` stale marker)

**Scope decision**:
- Diff exists + user did NOT ask for full → diff-only audit
- User says "全面" / "full check", OR no `scan/diff.txt` → full audit (read ALL scan files)

**If diff has no meaningful changes** (skip audit and tell user):
- Only PM refreshes: `~ packages.txt: scoop:`, `~ packages.txt: winget:`, `~ packages.txt: choco:`
- Only timestamp updates on same items (line changed but name unchanged, no `*` added)
- Empty diff: `"No changes."`
- Tell the user: "与上次扫描相比无明显变化，无需清理。如需全面审计请告诉我。/ No significant changes since last scan. Cleanup not needed. Let me know if you want a full audit."

### Step 3: Initial classify

Classification scope follows Step 2:
- **Full check** → classify ALL scan files
- **Diff only** → classify only items mentioned in the diff

For each scan file in scope:
- Read `scan/packages.txt` and `scan/manual-index.txt` as reference — these list all installed software
- Use `match` to batch-match all items against those references
- Match verdicts are **hints only**. The LLM makes the final decision.

**LLM must review every item**, including those with `active (package manager)` verdict.
The match table shows **who** each item matched against — use this to catch false matches:

- `Desktop` matched `winget: microsoft.dotnet.desktopruntime.7` → false match, Desktop = Windows folder → rule #1 `keep`
- `Project` matched `winget: obsproject.obsstudio` → false match, Project = user dev folder → rule #2 `keep`
- `go` matched `scoop: hugo-extended` → false match, go = Go workspace → check if `scoop: go` actually installed

For each item, work through the **Classification Rules** table top-to-bottom. The two core questions remain: **which software created this? Is that software still installed and used?**

```bash
uv run python -m src match scan/diff.txt
uv run python -m src match scan/home.txt
uv run python -m src match "dirname"
```

### Step 4: Investigation

For items not classified as keep/delete in Step 3 (including uncertain match results). For each item: **which software created this? Is it still installed?**

1. **Batch deep scan** — pass all unclassified items as a file or list, do NOT deep scan one by one.
   - Look for: identifiable file names (`.exe`, `.dll`, `.ini`, `.cfg` that name the software), recent timestamps, config file content that reveals the source
   - A `.exe` or `.dll` with a recognizable name → software is likely still installed → check PM
   - Only old `.log` files or empty subdirs → likely stale → `delete` or `remind`

2. **Check own knowledge** — many folder names are well-known software:
   - Game studios: `FromSoftware`, `CD Projekt Red`, `Larian Studios`, `Bethesda`, etc.
   - Dev tools: `clink`, `tauri`, `nwjs`, etc.
   - Chinese software: `Baidu`, `Tencent`, `NetEase`, `kingsoft` (WPS), etc.
   - If you recognize it, classify immediately — no need for web search

3. **Web search** — use ANY available tool: WebSearch, tavily, exa, firecrawl.
   - English: `"dirname" Windows AppData folder what software`
   - Chinese: `"dirname" 是什么软件的文件夹`
   - Chinese software: `"dirname" 软件 目录 AppData`
   - Game: `"dirname" game save folder PC`
   - If web search identifies the source → classify per rules #4–#8
   - If nothing found AND own knowledge insufficient:
     - stale item (`*`) → `remind`
     - non-stale item → `unknown`

**Minimize `unknown`.** Most folder names identify their software. `unknown` is only for items truly untraceable after all tools exhausted.

```bash
uv run python -m src deep "name1" "name2" "name3"
uv run python -m src deep scan/home.txt
```

### Step 5: Build report incrementally

Do NOT write the report markdown directly — use the `report` tool. This prevents format errors, 
duplicate entries, and miscounts.

**Workflow:**

```bash
# 1. Initialize
uv run python -m src report init

# 2. Classify items in batches. Write each batch to a temp file:
#    Format: path | source | description | evidence  (one per line)
#    Example batch file content:
#    .ssh | OpenSSH | SSH 密钥与配置 / SSH keys and config | 核心开发配置 / Core dev config
#    Desktop | Windows | 用户桌面 / User desktop | Windows system directory

# 3. Add batches to the report data:
uv run python -m src report add keep home batch-keep-home.txt
uv run python -m src report add delete appdata/local batch-delete-local.txt
# ... repeat for all sections and scan_keys

# 4. Build and verify:
uv run python -m src report status

# 5. On FAIL — read scan/verify-YYYY-MM-DD.txt for missing items,
#    classify them, write new batch files, add, and repeat from step 4.
#    On OK → done.
```

**The model writes item files, NOT the report.** The `report build` command handles all formatting,
counting, and section ordering. The model only needs to get the pipe-delimited items right.

**Batch strategy:**
- Start with obvious items: system dirs (rule #1), user data (rule #2), cache/temp (rule #4)
- Then software items (rules #5–#7) using match results
- Finally unknown items (rule #8) after web search
- Each batch can be one or many items — add frequently to avoid losing work

**Item file format:**
```
path | source | description | evidence
```
- All 4 fields required
- `path`: exact name as it appears in scan file
- `source`: software name when known. If the source is still unidentified after investigation, use `Unknown / 未识别来源`.
- Example unknown row: `mystery-dir | Unknown / 未识别来源 | 未识别来源的旧配置目录 / Old config directory with unidentified source | Cannot determine source`
- `description`: bilingual (中/英). **Explain what the software DOES**, not just its name.
  The user may not recognize every software by name — the description is how they decide.
  - Good: `OBS 录屏/直播软件 / Screen recording and streaming software`
  - Good: `游戏多媒体引擎 SDK，Party Animals 语音组件 / Game Multimedia Engine SDK, voice chat used by Party Animals`
  - Bad: `Party Animals GME SDK 残留` (just repeats the acronym, user still doesn't know what GME is)
  - Bad: `oopz 游戏工具` (too vague — what kind of tool? voice? graphics?)
- `evidence`: follow Evidence format table at top of this skill

### Step 6: Present (bilingual)

Once `report status` passes, tell the user counts and ask whether to proceed with cleanup.

If user confirms cleanup → invoke `cleaner-clean` skill.

### Step 7: Cleanup temporary files

After the audit is complete AND the user confirms cleanup AND has no further objections:

1. Delete batch files: `scan/batch-*.txt`
2. Delete report data: `scan/report-data/`
3. Delete verify residue: `scan/verify-*.txt`

```bash
Remove-Item scan/batch-*.txt -Force
Remove-Item scan/report-data/ -Recurse -Force
Remove-Item scan/verify-*.txt -Force -ErrorAction SilentlyContinue
```

**Keep**: scan output (`scan/*.txt`), partial deep scan results (`scan/partial/`).
Scan output is needed for future diffs.

**diff.txt vs report**: independent. `diff.txt` is a scan artifact (current scan vs last scan), used to decide audit scope. Report is the human-readable classification output. Deleting the report does not affect future diffs.

**Note**: report deletion (`report-*.md`) happens in `cleaner-clean` after cleanup is confirmed, not here.

**When to run**: only after user explicitly confirms cleanup is done and expresses no objections.
Do NOT run if the user still has questions about any item.

## Quick Reference

| Tool | Command | Purpose |
|------|---------|---------|
| scan | `uv run python -m src scan` | Full scan |
| match | `uv run python -m src match "name"` | Fuzzy match single item |
| match | `uv run python -m src match scan/diff.txt` | Batch match all items in file |
| deep | `uv run python -m src deep <name\|file> [name...] [--depth N]` | Inspect contents |
| report init | `uv run python -m src report init` | Start new report |
| report add | `uv run python -m src report add <section> <key> <file>` | Add items from batch file |
| report status | `uv run python -m src report status` | Build + verify, show missing |
| report remove | `uv run python -m src report remove <section> <key> <path>` | Remove one item |

| Action | Meaning | Rule |
|--------|---------|------|
| delete | Uninstalled software residual, or pure cache/temp, or empty dir | #3, #4, #5 |
| remind | Item is stale (`*`) — user should decide; also catch-all for uncertain stale items | #6 |
| keep | System, user data, or active software | #1, #2, #7 |
| unknown | Cannot identify source after full investigation | #8 |

## facts.md

Read for context before classification. It is a user-maintained hint file, not an authority that replaces scan/deep/match/verify. Only write when user explicitly requests. See `cleaner-config` for format.
