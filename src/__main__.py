import sys
import re
from pathlib import Path

from .config import load_config, load_facts, scan_dir, partial_dir
from .scanner import run_full_scan, run_partial_scan, deep_scan, _key_to_filename
from .packages import query_all, scan_manual_index, scan_steam_index
from .matcher import match_entry
from .cleaner import remove_entry


def _safe(text: str) -> str:
    """Replace non-ASCII chars that GBK terminal can't render."""
    try:
        text.encode("gbk")
        return text
    except UnicodeEncodeError:
        return text.encode("gbk", errors="replace").decode("gbk")


def _get_timestamp():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


def _load_scan_names():
    """Load all item names from scan txt files, categorized."""
    sd = scan_dir()
    config = load_config()
    home_names = []
    appdata_names = []
    for key in config.get("scan_dirs", {}):
        fp = sd / _key_to_filename(key)
        if not fp.exists():
            continue
        target = home_names if key == "home" else appdata_names
        for line in fp.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            m = re.match(r'(.+?)\s+(dir|file)\s*', line)
            if m:
                target.append(m.group(1).strip())
    return {"home": home_names, "appdata": appdata_names}


def _get_scan_file_mapping(config: dict) -> dict[str, str]:
    """Build {config_key: filename} from scan_dirs config, plus packages/manual-index."""
    mapping = {}
    for key in config.get("scan_dirs", {}):
        mapping[key] = _key_to_filename(key)
    mapping["packages"] = "packages.txt"
    mapping["manual-index"] = "manual-index.txt"
    mapping["steam-index"] = "steam-index.txt"
    return mapping


def cmd_scan(args):
    config = load_config()
    run_full_scan(config)


def cmd_scan_partial(key):
    config = load_config()
    run_partial_scan(key, config)


def cmd_deep(names: list[str], args=None):
    from rich.console import Console
    console = Console()
    config = load_config()
    pd = partial_dir()
    pd.mkdir(parents=True, exist_ok=True)

    # Depth: CLI --depth > config deep_scan_depth > default 3
    depth = config.get("deep_scan_depth", 3)
    if args and "--depth" in args:
        idx = args.index("--depth")
        if idx + 1 < len(args):
            depth = int(args[idx + 1])

    # File mode: single arg that is a file path
    if len(names) == 1:
        arg_path = Path(names[0])
        if arg_path.is_file():
            items = _extract_names_from_file(arg_path)
            names = [n for n, _ in items]

    depth_label = 'unlimited' if depth == -1 else f'depth {depth}'
    for i, name in enumerate(names):
        result = deep_scan(name, depth=depth)
        out_file = pd / f"{name.replace('/', '_').replace(chr(92), '_')}.txt"
        out_file.write_text(result, encoding="utf-8")
        if len(names) > 1:
            console.print(f"\n[bold green][{i+1}/{len(names)}] {name} → {out_file}[/bold green]")
        else:
            console.print(f"[bold green]Deep scan ({depth_label}) written to {out_file}[/bold green]")
        console.print(result)


_PM_HEADERS = {"scoop:", "winget:", "choco:", "mise:", "uv_tool:"}


def _extract_names_from_file(path: Path) -> list[tuple[str, str]]:
    """Extract item names from a scan file or diff file.

    Returns list of (name, line) tuples for context.
    """
    items = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        # Diff format: "  ~ filename: name" or "+ name" / "- name" / "~ name"
        m = re.match(r'\s*[+\-~]\s+\S+?:\s*(.+)', line)
        if m:
            name = m.group(1).strip()
            if name not in _PM_HEADERS:
                items.append((name, stripped))
            continue
        m = re.match(r'\s*[+\-~]\s+(.+)', line)
        if m:
            items.append((m.group(1).strip(), stripped))
            continue
        # Scan format: name  type  ...
        m = re.match(r'(.+?)\s+(dir|file)\s*', line)
        if m:
            items.append((m.group(1).strip(), stripped))
    return items


def _display_single_match(console, name, result):
    """Display match results for a single item in full table format."""
    from rich.table import Table
    table = Table(title=f'Match: "{name}"')
    table.add_column("Source", style="cyan")
    table.add_column("Match", style="green")
    table.add_column("Score", justify="right")

    for label, key in [("packages", "packages"), ("manual", "manual"), ("steam", "steam"), ("home", "home"), ("appdata", "appdata")]:
        matches = result[key]
        if matches:
            for m, score in matches[:3]:
                table.add_row(label, _safe(m), str(score))
        else:
            table.add_row(label, "(no match)", "")

    console.print(table)
    console.print(f"\n[bold]Verdict:[/bold] {result['verdict']}")


def _display_batch_match(console, results: list[dict]):
    """Display batch match results in compact table format."""
    from rich.table import Table

    table = Table(title=f"Batch match ({len(results)} items)")
    table.add_column("Name", style="cyan")
    table.add_column("Verdict", style="green")
    table.add_column("Top match", style="yellow")
    table.add_column("Score", justify="right")

    for r in results:
        name = _safe(r["query"])
        verdict = _safe(r["verdict"])
        best = ("", "", 0)
        for label in ("packages", "manual", "steam"):
            if r[label] and r[label][0][1] > best[2]:
                best = (label, r[label][0][0], r[label][0][1])
        if best[2] == 0:
            for label in ("home", "appdata"):
                if r[label] and r[label][0][1] > best[2]:
                    best = (label, r[label][0][0], r[label][0][1])
        top = _safe(f"{best[0]}: {best[1]}") if best[2] > 0 else "(no match)"
        table.add_row(name, verdict, top, str(best[2]) if best[2] > 0 else "")

    console.print(table)


def cmd_match(name):
    config = load_config()
    from rich.console import Console
    console = Console()

    # File mode: argument is a path to a scan/diff file
    arg_path = Path(name)
    if arg_path.is_file():
        items = _extract_names_from_file(arg_path)
        if not items:
            console.print(f"[yellow]No items found in {name}[/yellow]")
            return
        packages = query_all(config)
        manual = scan_manual_index(config)
        steam, _libraries = scan_steam_index(config)
        scan_names = _load_scan_names()
        results = []
        for item_name, _line in items:
            r = match_entry(item_name, packages, manual, steam, scan_names["home"], scan_names["appdata"])
            results.append(r)
        _display_batch_match(console, results)
        return

    # Single-item mode (original behavior)
    packages = query_all(config)
    manual = scan_manual_index(config)
    steam, _libraries = scan_steam_index(config)
    scan_names = _load_scan_names()

    result = match_entry(name, packages, manual, steam, scan_names["home"], scan_names["appdata"])
    _display_single_match(console, name, result)


def _filename_to_key(config: dict) -> dict[str, str]:
    """Reverse map: filename → config key."""
    mapping = {}
    for key in config.get("scan_dirs", {}):
        mapping[_key_to_filename(key)] = key
    return mapping


def _extract_diff_items(diff_path: Path, file_to_key: dict) -> dict[str, list[str]]:
    """Extract items from diff.txt, grouped by config key."""
    items: dict[str, list[str]] = {}
    if not diff_path.exists():
        return items
    for line in diff_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*[+\-~]\s+(\S+?):\s*(.+)', line)
        if not m:
            continue
        fname = m.group(1)
        name = m.group(2).strip()
        if name in _PM_HEADERS:
            continue
        key = file_to_key.get(fname)
        if not key:
            continue
        items.setdefault(key, []).append(name)
    return items


def _facts_constraints() -> tuple[set[str], set[str], set[str]]:
    facts = load_facts()

    def _names(entries) -> set[str]:
        names = set()
        for entry in entries:
            if isinstance(entry, str):
                names.add(entry.strip())
            elif isinstance(entry, dict):
                path = str(entry.get("path", "")).strip()
                if path:
                    names.add(Path(path).name)
        return {name for name in names if name}

    return (
        _names(facts.get("must_keep", [])),
        _names(facts.get("must_delete", [])),
        _names(facts.get("must_remind", [])),
    )


def cmd_verify(report_path):
    """Verify report items against scan/diff files."""
    from datetime import datetime
    sd = scan_dir()
    config = load_config()

    scan_mapping = _get_scan_file_mapping(config)

    # Collect scan item names per key (skip PM section headers)
    scan_items = {}
    scan_counts = {}
    for key, fname in scan_mapping.items():
        fp = sd / fname
        items = []
        hash_count = 0
        if fp.exists():
            for line in fp.read_text(encoding="utf-8").splitlines():
                if line.strip() and not line.startswith("#"):
                    m = re.match(r'(.+?)\s+(dir|file)\s*', line)
                    if m:
                        name = m.group(1).strip()
                        if re.fullmatch(r'[0-9a-f]{64}', name):
                            hash_count += 1
                        else:
                            items.append(name)
                    else:
                        parts = line.split()
                        if parts:
                            name = parts[0]
                            if name in _PM_HEADERS:
                                continue
                            if re.fullmatch(r'[0-9a-f]{64}', name):
                                hash_count += 1
                            else:
                                items.append(name)
        scan_items[key] = set(items)
        scan_counts[key] = len(items) + hash_count
        scan_items[f"{key}:hash"] = hash_count

    # Load diff items
    file_to_key = _filename_to_key(config)
    diff_items = _extract_diff_items(sd / "diff.txt", file_to_key)
    diff_counts = {k: len(v) for k, v in diff_items.items()}

    # Parse report — collect both counts and item names per directory
    rp = Path(report_path)
    if not rp.exists():
        print(f"Report not found: {report_path}")
        sys.exit(1)

    report_text = rp.read_text(encoding="utf-8")
    report_items: dict[str, list[str]] = {}
    report_counts: dict[str, int] = {}
    report_sections: dict[str, set[str]] = {
        "delete": set(),
        "recommend-delete": set(),
        "remind": set(),
        "keep": set(),
        "unknown": set(),
    }
    current_dir = None
    in_classification = False
    current_section = None

    for line in report_text.splitlines():
        if (
            line.startswith("## delete")
            or line.startswith("## recommend-delete")
            or line.startswith("## keep")
            or line.startswith("## unknown")
            or line.startswith("## remind")
        ):
            in_classification = True
            current_section = line[3:].strip()
        elif line.startswith("## "):
            in_classification = False
            current_dir = None
            current_section = None
        elif line.startswith("### ") and in_classification:
            dir_name = line[4:].strip()
            if "(" in dir_name:
                dir_name = dir_name[:dir_name.index("(")].strip()
            current_dir = dir_name
        elif line.startswith("|") and current_dir and in_classification:
            cells = [c.strip() for c in line.split("|")]
            if cells and cells[1] and cells[1] not in ("Path", "---", "------"):
                name = cells[1]
                batch_match = re.search(r'\((\d+)\)', name)
                count = int(batch_match.group(1)) if batch_match else 1
                report_counts[current_dir] = report_counts.get(current_dir, 0) + count
                report_items.setdefault(current_dir, []).append(name)
                if current_section in report_sections:
                    report_sections[current_section].add(name)

    # Detect mode
    diff_exists = (sd / "diff.txt").exists()
    is_diff = bool(diff_items)
    if diff_exists and not is_diff:
        print("Diff has no meaningful items. Nothing to verify.")
        return
    # Reference-only keys — not audited
    _REF_KEYS = {"packages", "manual-index", "steam-index"}
    target_items = (
        {k: v for k, v in diff_items.items() if k not in _REF_KEYS}
        if is_diff
        else {k: list(v) for k, v in scan_items.items() if not k.endswith(":hash") and k not in _REF_KEYS}
    )
    target_counts = (
        {k: v for k, v in diff_counts.items() if k not in _REF_KEYS}
        if is_diff
        else {k: v for k, v in scan_counts.items() if not k.endswith(":hash") and k not in _REF_KEYS}
    )

    # Check per directory
    from collections import Counter
    all_dirs = sorted(set(list(report_counts.keys()) + list(target_counts.keys())))
    mismatches = []
    for dir_name in all_dirs:
        rc = report_counts.get(dir_name, 0)
        tc = target_counts.get(dir_name, 0)
        if rc != tc:
            report_counter = Counter(report_items.get(dir_name, []))
            target_counter = Counter(target_items.get(dir_name, []))
            missing = sorted((target_counter - report_counter).elements())
            extra = sorted((report_counter - target_counter).elements())
            dupes = sorted(k for k, v in report_counter.items() if v > 1)
            mismatches.append((dir_name, tc, rc, missing, extra, dupes))

    if not mismatches:
        total = sum(report_counts.values())
        must_keep, must_delete, must_remind = _facts_constraints()
        facts_errors = []

        for name in sorted(must_keep):
            if name not in report_sections["keep"]:
                facts_errors.append(f"must_keep not in keep: {name}")
        for name in sorted(must_delete):
            if name not in report_sections["delete"]:
                facts_errors.append(f"must_delete not in delete: {name}")
        for name in sorted(must_remind):
            if name not in report_sections["remind"]:
                facts_errors.append(f"must_remind not in remind: {name}")

        if not facts_errors:
            print(f"OK — {total} items verified ({'diff' if is_diff else 'full'} mode)")
            return

        print(f"FAIL — facts constraint mismatch(es) ({len(facts_errors)})")
        ts = datetime.now().strftime("%Y-%m-%d")
        mismatch_path = sd / f"verify-{ts}.txt"
        lines = [f"# Facts constraint mismatch — {ts}\n"]
        for item in facts_errors:
            lines.append(f"- {item}")
        mismatch_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Mismatch report: {mismatch_path}")
        sys.exit(1)

    # Print summary
    print(f"FAIL — {len(mismatches)} directory mismatch(es) ({'diff' if is_diff else 'full'} mode)")
    for dir_name, tc, rc, missing, extra, dupes in mismatches:
        print(f"  {dir_name}: report {rc}, {'diff' if is_diff else 'scan'} {tc}")

    # Write mismatch report
    ts = datetime.now().strftime("%Y-%m-%d")
    mismatch_path = sd / f"verify-{ts}.txt"
    lines = [f"# Verify mismatch — {ts} ({'diff' if is_diff else 'full'} mode)\n"]
    for dir_name, tc, rc, missing, extra, dupes in mismatches:
        lines.append(f"## {dir_name} (expected {tc}, got {rc})")
        if missing:
            lines.append(f"  missing ({len(missing)}):")
            for n in missing:
                lines.append(f"    {n}")
        if extra:
            lines.append(f"  extra ({len(extra)}):")
            for n in extra:
                lines.append(f"    {n}")
        if dupes:
            lines.append(f"  duplicate in report ({len(dupes)}):")
            for n in dupes:
                lines.append(f"    {n}")
        lines.append("")
    mismatch_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Mismatch report: {mismatch_path}")
    sys.exit(1)


def cmd_remove(paths):
    from rich.console import Console
    console = Console()
    for p in paths:
        console.print(f"[bold]Removing {p}...[/bold]")
        if input(f"  Confirm delete {p}? [y/N] ").strip().lower() == "y":
            remove_entry(p)
        else:
            console.print("  Skipped.")


def main():
    args = sys.argv[1:]

    if not args:
        config = load_config()
        keys = list(config.get("scan_dirs", {}).keys())
        print("Usage: uv run python -m src <command> [args]")
        print("Commands: scan, deep, match, verify, remove, report")
        print(f"\nScan keys: {', '.join(keys)}, packages, manual-index, steam-index")
        sys.exit(1)

    cmd = args[0]

    if cmd == "scan":
        if len(args) > 1:
            cmd_scan_partial(args[1])
        else:
            cmd_scan(args[1:])
    elif cmd == "deep":
        if len(args) < 2:
            print("Usage: uv run python -m src deep <name|file> [name...] [--depth N]")
            print("  Single:  uv run python -m src deep \"dirname\"")
            print("  Multi:   uv run python -m src deep \"name1\" \"name2\"")
            print("  File:    uv run python -m src deep scan/diff.txt")
            sys.exit(1)
        # Collect names (all args before --depth or end)
        deep_names = []
        rest = args[1:]
        for a in rest:
            if a == "--depth":
                break
            deep_names.append(a)
        cmd_deep(deep_names, rest[len(deep_names):])
    elif cmd == "match":
        if len(args) < 2:
            print("Usage: uv run python -m src match <name|file>")
            print("  Single:  uv run python -m src match \"dirname\"")
            print("  Batch:   uv run python -m src match scan/diff.txt")
            sys.exit(1)
        cmd_match(args[1])
    elif cmd == "verify":
        if len(args) < 2:
            print("Usage: uv run python -m src verify <report-path>")
            sys.exit(1)
        cmd_verify(args[1])
    elif cmd == "report":
        from .report import cmd_init, cmd_add, cmd_remove, cmd_build, cmd_status
        if len(args) < 2:
            print("Usage: uv run python -m src report <subcommand> [args]")
            print("  init                        Create empty report data dir")
            print("  add <section> <key> <file>  Add items from file")
            print("  build [report-path]         Generate report markdown")
            print("  status [report-path]        Build + verify, show missing")
            print("  remove <section> <key> <p>  Remove one item")
            sys.exit(1)
        sub = args[1]
        if sub == "init":
            cmd_init()
        elif sub == "add":
            if len(args) < 5:
                print("Usage: uv run python -m src report add <section> <scan_key> <items_file>")
                sys.exit(1)
            cmd_add(args[2], args[3], args[4])
        elif sub == "remove":
            if len(args) < 5:
                print("Usage: uv run python -m src report remove <section> <scan_key> <path>")
                sys.exit(1)
            cmd_remove(args[2], args[3], args[4])
        elif sub == "build":
            cmd_build(args[2] if len(args) > 2 else None)
        elif sub == "status":
            cmd_status(args[2] if len(args) > 2 else None)
        else:
            print(f"Unknown report subcommand: {sub}")
            sys.exit(1)
    elif cmd == "remove":
        if len(args) < 2:
            print("Usage: uv run python -m src remove <path> [path...]")
            sys.exit(1)
        cmd_remove(args[1:])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
