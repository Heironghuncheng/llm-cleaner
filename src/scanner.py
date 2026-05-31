import os
from datetime import datetime, timedelta
from pathlib import Path

from .config import scan_dir, partial_dir, user_home


def _get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


def _resolve_path(rel: str) -> Path:
    """Resolve a config path relative to user home. Empty string = home itself."""
    if not rel:
        return user_home()
    p = Path(rel)
    if p.is_absolute():
        return p
    return user_home() / p


def _key_to_filename(key: str) -> str:
    """Convert a scan_dirs key to an output filename. 'appdata/roaming' -> 'appdata_roaming.txt'"""
    return key.replace("/", "_") + ".txt"


def _format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0"
    for unit in ["", "K", "M", "G"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.0f}{unit}" if not unit else f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}T"


def _scan_directory(base: Path, max_depth: int = 1) -> list[dict]:
    """Scan a directory and collect metadata. No size calculation for dirs.
    max_depth=-1 means unlimited recursion."""
    items = []
    if not base.is_dir():
        return items

    def _walk(current: Path, depth: int, prefix: str = ""):
        try:
            for entry in os.scandir(current):
                rel = f"{prefix}{entry.name}" if prefix else entry.name
                try:
                    stat = entry.stat(follow_symlinks=False)
                    last_write = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                except OSError:
                    last_write = "?"

                if entry.is_dir(follow_symlinks=False):
                    items.append({
                        "name": entry.name,
                        "rel": rel,
                        "type": "dir",
                        "last_write": last_write,
                    })
                    if max_depth == -1 or depth < max_depth:
                        _walk(Path(entry.path), depth + 1, f"{rel}/")
                else:
                    items.append({
                        "name": entry.name,
                        "rel": rel,
                        "type": "file",
                        "size": stat.st_size,
                        "last_write": last_write,
                    })
        except PermissionError:
            pass

    _walk(base, 1)
    return items


def _format_scan_txt(header: str, items: list[dict], timestamp: str, stale_months: int = 1) -> str:
    """Format scan results. Items older than stale_months are tagged *."""
    lines = [f"# {header} — {timestamp}"]
    if stale_months > 0:
        cutoff = datetime.now() - timedelta(days=stale_months * 30)
    else:
        cutoff = None
    for item in items:
        name = item["name"]
        d = item["last_write"]
        date_compact = d[2:].replace("-", "") if len(d) == 10 else d
        is_stale = False
        if cutoff and item["last_write"] != "?":
            try:
                item_date = datetime.strptime(item["last_write"], "%Y-%m-%d")
                is_stale = item_date < cutoff
            except ValueError:
                pass
        stale_tag = " *" if is_stale else ""
        if item["type"] == "dir":
            lines.append(f"{name:<25} dir  {date_compact}{stale_tag}")
        else:
            size_str = _format_size(item.get("size", 0))
            lines.append(f"{name:<25} file {size_str:>6} {date_compact}{stale_tag}")
    return "\n".join(lines) + "\n"


def _scan_one(key: str, rel_path: str, depth: int, stale_months: int) -> str:
    """Scan one directory entry from config."""
    target = _resolve_path(rel_path)
    items = _scan_directory(target, max_depth=depth)
    return _format_scan_txt(f"{key} — {target}", items, _get_timestamp(), stale_months)


def deep_scan(name: str, depth: int = 3) -> str:
    """Deep scan a single item under user home. Includes file sizes only.
    depth=-1 means unlimited recursion."""
    target = user_home() / name
    if not target.exists():
        for sub in ["Roaming", "Local", "LocalLow"]:
            candidate = user_home() / "AppData" / sub / name
            if candidate.exists():
                target = candidate
                break

    if not target.exists():
        return f"# Deep scan: {name} — NOT FOUND\n"

    items = _scan_directory(target, max_depth=depth)
    ts = _get_timestamp()
    lines = [f"# deep: {name} — {ts}"]
    for item in items:
        indent = "  " * (item["rel"].count("/") - 1)
        d = item["last_write"]
        date_compact = d[2:].replace("-", "") if len(d) == 10 else d
        if item["type"] == "dir":
            lines.append(f"{indent}{item['rel']:<40} dir  {date_compact}")
        else:
            size_str = _format_size(item.get("size", 0))
            lines.append(f"{indent}{item['rel']:<40} file {size_str:>6} {date_compact}")
    return "\n".join(lines) + "\n"


def generate_diff(old_dir: Path, new_dir: Path) -> str:
    """Compare old and new scan files, generate diff text."""
    ts = _get_timestamp()
    lines = [f"# Diff — generated {ts}"]
    added = []
    removed = []
    changed = []

    for new_file in new_dir.glob("*.txt"):
        if new_file.name in ("diff.txt",):
            continue
        old_file = old_dir / new_file.name
        if not old_file.exists():
            continue

        old_entries = {}
        for line in old_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            name = line.split()[0] if line.split() else ""
            if name:
                old_entries[name] = line

        new_entries = {}
        for line in new_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            name = line.split()[0] if line.split() else ""
            if name:
                new_entries[name] = line

        for name in new_entries:
            if name not in old_entries:
                added.append(f"  + {new_file.name}: {name}")
        for name in old_entries:
            if name not in new_entries:
                removed.append(f"  - {new_file.name}: {name}")
        for name in new_entries:
            if name in old_entries and new_entries[name] != old_entries[name]:
                changed.append(f"  ~ {new_file.name}: {name}")

    if not added and not removed and not changed:
        lines.append("  No changes.")
    else:
        for a in added:
            lines.append(a)
        for r in removed:
            lines.append(r)
        for c in changed:
            lines.append(c)

    return "\n".join(lines) + "\n"


def run_full_scan(config: dict):
    """Run a full scan: all configured dirs + packages + manual index + steam index + diff."""
    from .packages import (
        query_all,
        scan_manual_index,
        scan_steam_index,
        format_packages_txt,
        format_manual_index_txt,
        format_steam_index_txt,
    )

    sd = scan_dir()
    pd = partial_dir()
    ts = _get_timestamp()
    stale_months = config.get("stale_months", 1)

    sd.mkdir(parents=True, exist_ok=True)
    pd.mkdir(parents=True, exist_ok=True)

    # Clear partial/
    if pd.exists():
        for f in pd.iterdir():
            f.unlink()

    # Save old scans for diff (only if previous scan files exist)
    old_scan_tmp = sd.parent / ".scan_old"
    if old_scan_tmp.exists():
        import shutil
        shutil.rmtree(old_scan_tmp)
    has_old = any(f.suffix == ".txt" for f in sd.iterdir()) if sd.exists() else False
    if has_old:
        import shutil
        shutil.copytree(sd, old_scan_tmp, ignore=shutil.ignore_patterns("partial", "diff.txt"))

    # Packages
    pkg_results = query_all(config)
    (sd / "packages.txt").write_text(format_packages_txt(pkg_results, ts), encoding="utf-8")

    # Manual index
    manual_names = scan_manual_index(config)
    (sd / "manual-index.txt").write_text(
        format_manual_index_txt(manual_names, ts, config.get("manual_dirs", [])),
        encoding="utf-8",
    )

    # Steam index
    steam_names, steam_libraries = scan_steam_index(config)
    (sd / "steam-index.txt").write_text(
        format_steam_index_txt(steam_names, ts, steam_libraries),
        encoding="utf-8",
    )

    # Configured directories
    scan_dirs = config.get("scan_dirs", {})
    scan_depths = config.get("scan_depths", {})
    default_depth = scan_depths.get("default", 1)

    for key, rel_path in scan_dirs.items():
        depth = scan_depths.get(key, default_depth)
        filename = _key_to_filename(key)
        target = _resolve_path(rel_path)
        items = _scan_directory(target, max_depth=depth)
        (sd / filename).write_text(
            _format_scan_txt(f"{key} — {target}", items, ts, stale_months),
            encoding="utf-8",
        )

    # Diff — skip on first scan (no previous data to compare)
    if old_scan_tmp.exists():
        diff_text = generate_diff(old_scan_tmp, sd)
        (sd / "diff.txt").write_text(diff_text, encoding="utf-8")
        import shutil
        shutil.rmtree(old_scan_tmp)


def run_partial_scan(key: str, config: dict):
    """Refresh a single scan directory by config key."""
    sd = scan_dir()
    sd.mkdir(parents=True, exist_ok=True)
    ts = _get_timestamp()
    stale_months = config.get("stale_months", 1)
    scan_dirs = config.get("scan_dirs", {})
    scan_depths = config.get("scan_depths", {})

    if key == "packages":
        from .packages import query_all, format_packages_txt
        pkg_results = query_all(config)
        (sd / "packages.txt").write_text(format_packages_txt(pkg_results, ts), encoding="utf-8")
    elif key == "manual-index":
        from .packages import scan_manual_index, format_manual_index_txt
        manual_names = scan_manual_index(config)
        (sd / "manual-index.txt").write_text(
            format_manual_index_txt(manual_names, ts, config.get("manual_dirs", [])),
            encoding="utf-8",
        )
    elif key == "steam-index":
        from .packages import scan_steam_index, format_steam_index_txt
        steam_names, steam_libraries = scan_steam_index(config)
        (sd / "steam-index.txt").write_text(
            format_steam_index_txt(steam_names, ts, steam_libraries),
            encoding="utf-8",
        )
    elif key in scan_dirs:
        rel_path = scan_dirs[key]
        depth = scan_depths.get(key, scan_depths.get("default", 1))
        filename = _key_to_filename(key)
        target = _resolve_path(rel_path)
        items = _scan_directory(target, max_depth=depth)
        (sd / filename).write_text(
            _format_scan_txt(f"{key} — {target}", items, ts, stale_months),
            encoding="utf-8",
        )
    else:
        print(f"Unknown scan key: {key}")
        print(f"Available: {', '.join(scan_dirs.keys())}, packages, manual-index, steam-index")
        return
