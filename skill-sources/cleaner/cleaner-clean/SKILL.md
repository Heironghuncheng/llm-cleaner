---
name: cleaner-clean
description: Use when the user has confirmed cleanup after an audit in this Cleaner project and deletion decisions need to be executed safely.
---

# Cleaner Clean

## Critical Guidelines

- You MUST confirm with user before deleting anything.
- You MUST only operate under %USERPROFILE%.
- You MUST offer `remind` items as optional deletions.
- You MUST treat `recommend-delete` items as deletion candidates that already passed a second review in `cleaner-audit`.

## When to Use

Invoked by `cleaner-audit` after user confirms cleanup. Not triggered directly.

## How to Use

All commands run from `~/Project/cleaner`.

### Step 1: Read report

Find all rows where Action = `delete`, `recommend-delete`, and `remind`.

### Step 2: Confirm

Bilingual confirmation prompt. This is the **batch confirmation** for the full deletion set before execution starts:

```
以下项目标记为待清理 (delete / recommend-delete):        Items marked for deletion:
- item1                               - item1
- item2                               - item2

以下项目标记为待观察 (remind)，是否也一并清理？
These items are marked as remind — clean them too?
- item3

即将删除以上项目，确认执行？ [y/N]
About to delete these items. Confirm? [y/N]
```

### Step 3: Execute

```bash
uv run python -m src remove "<path>"
```

One command per item. Paths relative to %USERPROFILE%.
`src remove` will ask again for each item, so the cleanup flow uses **double confirmation**:
- Step 2 confirms the whole batch
- `remove` confirms each path before deletion

### Step 4: Report results

```
清理完成 / Cleanup complete
已删除: N / Deleted: N
失败: N / Failed: N
```

### Step 5: Delete report

After cleanup is complete and user has no further objections, delete the report:

```bash
Remove-Item report-*.md -Force
```

Report is a one-time deliverable for this audit cycle — no longer needed after cleanup is confirmed.

## Quick Reference

| Safety rule | Detail |
|-------------|--------|
| Scope | %USERPROFILE% only |
| Confirmation | Batch confirm first, then per-item confirm during `remove` |
| facts.md | Only update when user explicitly requests |

See `cleaner-config` for facts.md writing conventions.
