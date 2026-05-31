"""Report builder — incremental report construction for LLM-driven audit.

Workflow:
  1. report init              → create empty data dir
  2. Write item files: scan/report-data/<section>-<scan_key>.txt
     Format: path | source | description | evidence  (one per line)
  3. report build             → generate report-YYYY-MM-DD.md
  4. report verify <report>   → check completeness
  5. Fix missing items → repeat from step 2
"""

import sys
from pathlib import Path
from datetime import datetime

from .config import scan_dir, load_config

_DATA_DIR_NAME = "report-data"
_SECTIONS = ("recommend-delete", "delete", "remind", "keep", "unknown")


def data_dir() -> Path:
    return scan_dir() / _DATA_DIR_NAME


def cmd_init():
    """Create empty report data directory."""
    d = data_dir()
    if d.exists():
        import shutil
        shutil.rmtree(d)
    d.mkdir(parents=True)
    print(f"Initialized {d}")


def _key_to_section_file(section: str, scan_key: str) -> str:
    safe = scan_key.replace("/", "_").replace("\\", "_")
    return f"{section}-{safe}.txt"


def _section_file_to_key(filename: str) -> tuple[str, str] | None:
    """Parse 'section-scan_key.txt' back to (section, scan_key)."""
    stem = filename.replace(".txt", "")
    for section in _SECTIONS:
        prefix = f"{section}-"
        if stem.startswith(prefix):
            return section, stem[len(prefix):].replace("_", "/")
    return None


def _parse_item(line: str) -> dict | None:
    """Parse one item line: path | source | description | evidence"""
    parts = [c.strip() for c in line.split("|", 3)]
    if len(parts) != 4:
        return None
    if not parts[0] or parts[0].startswith("#"):
        return None
    return {"path": parts[0], "source": parts[1], "description": parts[2], "evidence": parts[3]}


def cmd_add(section: str, scan_key: str, items_file: str):
    """Add items from a file to the report data.

    items_file: one item per line, format: path | source | description | evidence
    """
    src = Path(items_file)
    if not src.is_file():
        print(f"File not found: {items_file}")
        sys.exit(1)

    d = data_dir()
    if not d.exists():
        print("Run 'report init' first.")
        sys.exit(1)

    out_file = d / _key_to_section_file(section, scan_key)

    existing: set[str] = set()
    if out_file.exists():
        for line in out_file.read_text(encoding="utf-8").splitlines():
            item = _parse_item(line)
            if item:
                existing.add(item["path"])

    added = 0
    with open(out_file, "a", encoding="utf-8") as f:
        for line in src.read_text(encoding="utf-8").splitlines():
            item = _parse_item(line)
            if not item:
                continue
            if item["path"] in existing:
                continue
            f.write(line.strip() + "\n")
            existing.add(item["path"])
            added += 1

    print(f"Added {added} items to {out_file.name}")


def cmd_remove(section: str, scan_key: str, path: str):
    """Remove a single item from report data."""
    d = data_dir()
    f = d / _key_to_section_file(section, scan_key)
    if not f.exists():
        print(f"No data file for {section}/{scan_key}")
        return

    lines = f.read_text(encoding="utf-8").splitlines()
    kept = []
    removed = False
    for line in lines:
        item = _parse_item(line)
        if item and item["path"] == path:
            removed = True
            continue
        kept.append(line)

    if removed:
        content = "\n".join(kept) + "\n" if kept else ""
        f.write_text(content, encoding="utf-8")
        print(f"Removed '{path}' from {f.name}")
    else:
        print(f"'{path}' not found in {f.name}")


def cmd_build(report_path: str | None = None):
    """Build report markdown from data files."""
    d = data_dir()
    if not d.exists():
        print("Run 'report init' first.")
        sys.exit(1)

    config = load_config()
    scan_keys = list(config.get("scan_dirs", {}).keys())

    report: dict[str, dict[str, list[dict]]] = {section: {} for section in _SECTIONS}
    totals: dict[str, int] = {section: 0 for section in _SECTIONS}

    for f in sorted(d.iterdir()):
        if not f.suffix == ".txt":
            continue
        parsed = _section_file_to_key(f.name)
        if not parsed:
            continue
        section, scan_key = parsed
        if section not in report:
            continue
        items = []
        for line in f.read_text(encoding="utf-8").splitlines():
            item = _parse_item(line)
            if item:
                items.append(item)
        if items:
            report[section][scan_key] = items
            totals[section] += len(items)

    total = sum(totals.values())
    ts = datetime.now().strftime("%Y-%m-%d")
    out_path = Path(report_path) if report_path else Path(f"report-{ts}.md")

    lines = []
    lines.append(f"# Audit Report — {ts}")
    lines.append("")
    lines.append("## Summary")
    lines.append(
        f"- total: {total} | delete: {totals['delete']} | "
        f"recommend-delete: {totals['recommend-delete']} | "
        f"remind: {totals['remind']} | keep: {totals['keep']} | "
        f"unknown: {totals['unknown']}"
    )
    lines.append("")

    for section in _SECTIONS:
        lines.append(f"## {section}")
        section_data = report.get(section, {})
        ordered_keys = [k for k in scan_keys if k in section_data]
        if not ordered_keys:
            lines.append("")
            continue
        for sk in ordered_keys:
            items = section_data[sk]
            lines.append(f"### {sk} ({len(items)})")
            lines.append("| Path | Source | Description | Evidence |")
            lines.append("|------|--------|-----------|----------|")
            for item in items:
                lines.append(
                    f"| {item['path']} | {item['source']} | "
                    f"{item['description']} | {item['evidence']} |"
                )
            lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {out_path} ({total} items)")


def cmd_status(report_path: str | None = None):
    """Build report and run verify, showing what's missing."""
    ts = datetime.now().strftime("%Y-%m-%d")
    rp = report_path or f"report-{ts}.md"

    cmd_build(rp)

    from .__main__ import cmd_verify
    cmd_verify(rp)
