import shutil
from pathlib import Path

from rich.console import Console

from .config import user_home, scan_dir

console = Console()


def remove_entry(rel_path: str, dry_run: bool = False) -> bool:
    """Remove a file/directory under %USERPROFILE%. Returns True if removed."""
    target = user_home() / rel_path
    resolved = target.resolve()
    home_resolved = user_home().resolve()

    # Safety: ensure target is under user home
    try:
        resolved.relative_to(home_resolved)
    except ValueError:
        console.print(f"[bold red]Refused: {rel_path} is outside user home[/bold red]")
        return False

    if not resolved.exists():
        console.print(f"[yellow]Not found: {rel_path}[/yellow]")
        return False

    if dry_run:
        console.print(f"[dim]Would remove: {rel_path}[/dim]")
        return True

    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink()

    console.print(f"[bold green]Removed: {rel_path}[/bold green]")

    # Update scan files
    _remove_from_scan_files(rel_path)
    return True


def _remove_from_scan_files(rel_path: str):
    """Remove an entry from scan/*.txt files."""
    sd = scan_dir()
    name = rel_path.split("/")[-1].split("\\")[-1]

    for scan_file in sd.glob("*.txt"):
        if scan_file.name == "diff.txt":
            continue
        lines = scan_file.read_text(encoding="utf-8").splitlines()
        new_lines = [l for l in lines if not l.startswith(name + " ") and l.strip() != name]
        if len(new_lines) != len(lines):
            scan_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
