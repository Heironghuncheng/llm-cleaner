# llm-cleaner

Windows-first tooling for auditing leftover software files under `%USERPROFILE%`, plus a small set of Cleaner-specific agent skills.

This repository is prepared specifically for Windows and PowerShell workflows. Linux and macOS are not primary targets.
Its primary development purpose is to inspect and clean leftover software files inside the user's home directory.
The project workflows and Cleaner-specific skills support both Chinese and English.

## Scope

- Scan target: `%USERPROFILE%`
- Reference-only indexes: `C:\no_super`, `D:\game`
- Runtime outputs: `scan/` and `report-*.md`

## Quick Start

```powershell
uv sync
uv run python -m src scan
```

To reset the repository back to a never-used state:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reset-unused-state.ps1
```

The reset script removes generated scan/report artifacts, deletes local agent install state, deletes local Claude settings, and restores `facts.md` from `facts.template.md`.

## Repository Layout

- `src/`: core scan, match, verify, report, and remove logic
- `scripts/reset-unused-state.ps1`: cleanup script for returning the repo to an unused state
- `skill-sources/cleaner/`: tracked source copies of Cleaner-specific skills
- `.agents/skills/` and `.claude/skills/`: local agent install state, intentionally ignored

## Skills

Cleaner-specific skill sources are grouped under `skill-sources/cleaner/`:

These skill files were drafted with AI assistance, then manually reviewed and verified before being published in this repository.

- `cleaner-audit`
- `cleaner-clean`
- `cleaner-config`
- `cleaner-first-use`

## TODO

- [ ] 把项目转化成标准的skill仓库
