# llm-cleaner

用于审计和清理 Windows 用户目录中残留软件文件的工具，并附带一组 Cleaner 专用 agent skills。  
Windows-first tooling for auditing and cleaning leftover software files inside the user's home directory, plus a small set of Cleaner-specific agent skills.

本仓库专门面向 Windows 和 PowerShell 工作流准备，Linux 和 macOS 不是主要目标平台。  
This repository is prepared specifically for Windows and PowerShell workflows. Linux and macOS are not primary targets.

项目的主要开发目的，是检查并清理用户主目录中的残留软件文件。  
Its primary development purpose is to inspect and clean leftover software files inside the user's home directory.

## 范围 / Scope

- 扫描目标：`%USERPROFILE%`
  Scan target: `%USERPROFILE%`
- 运行产物：`scan/` 与 `report-*.md`
  Runtime outputs: `scan/` and `report-*.md`

## 快速开始 / Quick Start

```powershell
uv sync
uv run python -m src scan
```

如需将仓库恢复到从未使用的状态，请运行：  
To reset the repository back to a never-used state, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reset-unused-state.ps1
```

该脚本会删除扫描与报告产物，并用 `facts.template.md` 重新生成 `facts.md`。  
The reset script removes generated scan/report artifacts and restores `facts.md` from `facts.template.md`.

## 仓库结构 / Repository Layout

- `src/`: 核心扫描、匹配、校验、报告与删除逻辑  
  Core scan, match, verify, report, and remove logic
- `scripts/reset-unused-state.ps1`: 将仓库恢复到未使用状态的脚本  
  Script for returning the repository to an unused state
- `skill-sources/cleaner/`: Cleaner 专用 skills 的跟踪源文件  
  Tracked source copies of Cleaner-specific skills

当前还支持一个 Steam 游戏参考索引，会读取 Steam 库配置与已安装游戏清单。  
The project also supports a Steam game reference index by reading Steam library configuration and installed game manifests.

## Skills

Cleaner 专用 skills 的源文件集中在 `skill-sources/cleaner/`。  
Cleaner-specific skill sources are grouped under `skill-sources/cleaner/`.

这些 skill 文件由 AI 辅助起草，并在发布到仓库前经过人工审核与验证。  
These skill files were drafted with AI assistance, then manually reviewed and verified before being published in this repository.

`facts.md` 现在用于存放硬约束，只保留三类：`must_keep`、`must_delete`、`must_remind`。  
`facts.md` now stores hard constraints only, with three categories: `must_keep`, `must_delete`, and `must_remind`.

- `cleaner-audit`
- `cleaner-clean`
- `cleaner-config`
- `cleaner-first-use`

## TODO

- [ ] 把项目转化成标准的 skill 仓库 / Convert the project into a standard skill repository
