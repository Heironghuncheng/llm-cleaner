---
name: cleaner-first-use
description: Use when a user is setting up this Cleaner project for the first time and needs guided initial configuration before the first scan or audit.
---

# Cleaner First Use

Guide the user through Cleaner onboarding step by step. This skill handles the first-use conversation flow; use `cleaner-config` for the actual file edits.

## When to use

- User says `首次使用` / `第一次用` / `初始化` / `setup` / `first use`
- User wants help configuring `config.json` before the first real scan
- User wants to define hard `facts.md` constraints before running an audit

Do not use for:
- Routine config edits after onboarding; use `cleaner-config`
- Leftover classification work; use `cleaner-audit`
- Deletion execution; use `cleaner-clean`

## Instructions

### 1. Explain scope first

Before asking configuration questions, state these guardrails:
- Cleaner only scans under `%USERPROFILE%`
- `C:\no_super` and `D:\game` are reference indexes only and are never cleaned
- `facts.md` stores hard constraints, not soft hints
- The first-use goal is safe defaults plus a successful first scan

### 2. Review current defaults

Read `config.json` and summarize only the settings the user may want to change:
- `scan_dirs`
- `scan_depths`
- `manual_dirs`
- `package_managers`
- `stale_months`
- `deep_scan_depth`

Do not edit anything yet.

### 3. Ask one setup question at a time

Ask the next unanswered question only. Keep prompts bilingual.

Recommended order:
1. Keep the default scan scope: `home`, `appdata/root`, `appdata/roaming`, `appdata/local`, `appdata/locallow`?
2. Keep the current reference dirs in `manual_dirs`?
3. Keep the current `package_managers` list?
4. Change `stale_months`?
5. Change `deep_scan_depth`? Explain that `-1` means unlimited deep scan.
6. Add any explicit `facts.md` constraints, such as `must_keep`, `must_delete`, or `must_remind` entries?

Rules:
- Do not dump the whole questionnaire in one message
- Do not write `facts.md` unless the user gives explicit constraint items
- Do not propose scan roots outside the project scope without a clear user request
- If the user is unsure, keep the current default

### 4. Apply changes in small batches

When the user has answered enough to act:
- Use `cleaner-config` for actual edits
- Group related `config.json` changes together
- Keep `facts.md` entries minimal, explicit, and user-provided
- Prefer the current project defaults unless the user clearly wants a change

### 5. Validate before handoff

After changes:
- If `scan_dirs` or `scan_depths` changed, run `uv run python -m src scan <key>` for each changed key
- If `manual_dirs` changed, run `uv run python -m src scan manual-index`
- If `package_managers` changed, run `uv run python -m src scan packages`
- Then run `uv run python -m src scan`

Fail fast:
- If any validation command fails, report the exact command and stop
- Do not continue to audit until the first full scan succeeds

### 6. Close the onboarding

Summarize:
- Final settings changed in `config.json`
- Any `facts.md` entries added
- Whether the first full scan succeeded
- The next step: switch to `cleaner-audit` if the user wants the first audit

## Quick Reference

| Need | Action |
|------|--------|
| First-time setup | Use this skill |
| Actual config edit | Use `cleaner-config` |
| Validate package manager list | `uv run python -m src scan packages` |
| Validate manual references | `uv run python -m src scan manual-index` |
| Validate one scan target | `uv run python -m src scan <key>` |
| Final onboarding check | `uv run python -m src scan` |
