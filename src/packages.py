import subprocess
import json
import os
import re
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None


def _run(cmd: list[str], timeout: int = 30, use_powershell: bool = False) -> str:
    """Run a command, return stdout. Handle encoding gracefully."""
    try:
        if use_powershell:
            ps_cmd = (
                f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                f"$OutputEncoding = [System.Text.Encoding]::UTF8; "
                f"{cmd}"
            )
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, timeout=timeout,
                encoding="utf-8", errors="replace",
            )
        else:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            r = subprocess.run(
                cmd, capture_output=True, timeout=timeout,
                encoding="utf-8", errors="replace", env=env,
            )
        return r.stdout or ""
    except Exception:
        return ""


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    import re
    return re.sub(r'\x1b\[[0-9;]*[mK]', '', text)


def query_scoop() -> list[str]:
    out = _run("scoop list | Out-String", use_powershell=True)
    out = _strip_ansi(out)
    names = []
    for line in out.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("Name") or line.startswith("----") or line.startswith("Installed"):
            continue
        parts = line.split()
        if parts and parts[0] and not parts[0].startswith("["):
            names.append(parts[0].lower())
    return names


def query_winget() -> list[str]:
    import tempfile, re
    names = []

    # Pass 1: winget export JSON (winget-managed packages only)
    tmp = tempfile.mktemp(suffix=".json")
    try:
        _run(f"winget export -o {tmp} --accept-source-agreements | Out-Null", use_powershell=True)
        if os.path.exists(tmp):
            data = json.loads(Path(tmp).read_text(encoding="utf-8"))
            for pkg in data.get("Sources", [{}])[0].get("Packages", []):
                name = pkg.get("PackageIdentifier", "")
                if name:
                    names.append(name.lower())
    except Exception:
        pass
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    # Pass 2: winget list for ARP entries (externally installed software)
    out = _run("winget list --accept-source-agreements | Out-String", use_powershell=True, timeout=60)
    out = _strip_ansi(out)
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] and not parts[0].startswith("-") and not parts[0].startswith("Name"):
            name = parts[0]
            # Filter out header/meta lines
            if name in ("Installed", "No installed"):
                continue
            names.append(name.lower())

    return list(set(names))


def query_choco() -> list[str]:
    ps = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "choco list 2>$null | Out-String"
    )
    out = _run(ps, use_powershell=True)
    names = []
    for line in out.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("Chocolatey") or line.startswith("packages"):
            continue
        parts = line.split()
        if parts and parts[0] and not parts[0].startswith("|"):
            names.append(parts[0].lower())
    return names


def query_mise() -> list[str]:
    out = _run(["mise", "list"])
    names = []
    for line in out.strip().splitlines():
        parts = line.split()
        if parts:
            names.append(parts[0].lower())
    return names


def query_uv_tool() -> list[str]:
    out = _run(["uv", "tool", "list"])
    names = []
    for line in out.strip().splitlines():
        line = line.strip()
        if line and not line.startswith("-"):
            name = line.split()[0].lower()
            names.append(name)
    return names


def _normalize_windows_path(raw: str) -> Path:
    return Path(raw.replace("\\\\", "\\").replace("/", "\\"))


def _steam_roots_from_registry() -> list[Path]:
    if winreg is None:
        return []

    roots = []
    reg_queries = [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamExe"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ]

    for hive, subkey, value_name in reg_queries:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
        except OSError:
            continue

        path = _normalize_windows_path(str(value))
        if value_name.lower().endswith("exe"):
            path = path.parent
        if path.is_dir():
            roots.append(path)

    unique = []
    seen = set()
    for root in roots:
        key = str(root).lower()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def discover_steam_libraries(config: dict) -> list[Path]:
    configured = [_normalize_windows_path(p) for p in config.get("steam_roots", []) if p]
    roots = configured + _steam_roots_from_registry()

    libraries = []
    seen = set()

    for raw_root in roots:
        root = raw_root.parent if raw_root.name.lower() == "steamapps" else raw_root
        candidates = [root]

        libraryfolders = root / "steamapps" / "libraryfolders.vdf"
        if libraryfolders.is_file():
            text = libraryfolders.read_text(encoding="utf-8", errors="replace")
            path_values = re.findall(r'"path"\s*"([^"]+)"', text, flags=re.IGNORECASE)
            if not path_values:
                path_values = [value for _key, value in re.findall(r'"(\d+)"\s*"([^"]+)"', text)]
            candidates.extend(_normalize_windows_path(value) for value in path_values)

        for candidate in candidates:
            if (candidate / "steamapps").is_dir():
                key = str(candidate).lower()
                if key not in seen:
                    seen.add(key)
                    libraries.append(candidate)

    return libraries


def scan_steam_index(config: dict) -> tuple[list[str], list[str]]:
    libraries = discover_steam_libraries(config)
    names = []

    for library in libraries:
        for manifest in (library / "steamapps").glob("appmanifest_*.acf"):
            text = manifest.read_text(encoding="utf-8", errors="replace")
            match = re.search(r'"name"\s*"([^"]+)"', text, flags=re.IGNORECASE)
            if not match:
                match = re.search(r'"installdir"\s*"([^"]+)"', text, flags=re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if name:
                    names.append(name)

    return sorted(set(names)), [str(path) for path in libraries]


def query_all(config: dict) -> dict[str, list[str]]:
    results = {}
    pm_map = {
        "scoop": query_scoop,
        "winget": query_winget,
        "choco": query_choco,
        "mise": query_mise,
        "uv_tool": query_uv_tool,
    }
    for pm in config.get("package_managers", []):
        fn = pm_map.get(pm)
        if fn:
            results[pm] = fn()
    return results


def scan_manual_index(config: dict) -> list[str]:
    """Scan manual_dirs for subdirectory names."""
    names = []
    for d in config.get("manual_dirs", []):
        p = Path(d)
        if p.is_dir():
            for child in p.iterdir():
                if child.is_dir():
                    names.append(child.name)
    return sorted(set(names))


def format_packages_txt(results: dict[str, list[str]], timestamp: str) -> str:
    lines = [f"# Packages — scanned {timestamp}"]
    for pm, names in results.items():
        lines.append(f"{pm}: {', '.join(names)}")
    return "\n".join(lines) + "\n"


def format_manual_index_txt(names: list[str], timestamp: str, sources: list[str]) -> str:
    lines = [
        f"# Manual index — scanned {timestamp}",
        f"# Source: {', '.join(sources)}",
        "# These dirs are NOT cleaned — only used as reference",
    ]
    for n in names:
        lines.append(n)
    return "\n".join(lines) + "\n"


def format_steam_index_txt(names: list[str], timestamp: str, libraries: list[str]) -> str:
    lines = [
        f"# Steam index — scanned {timestamp}",
        f"# Libraries: {', '.join(libraries) if libraries else '(none detected)'}",
        "# Installed Steam game names used as reference only",
    ]
    for name in names:
        lines.append(name)
    return "\n".join(lines) + "\n"
