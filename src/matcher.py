from thefuzz import fuzz


def normalize(name: str) -> str:
    """Normalize a name for matching: lowercase, strip common suffixes."""
    n = name.lower().strip().strip(".")
    # Remove common file extensions
    for ext in [".txt", ".exe", ".bat", ".cmd", ".json", ".yaml", ".yml"]:
        if n.endswith(ext):
            n = n[: -len(ext)]
    return n


def fuzzy_match(query: str, candidates: list[str], threshold: int = 70) -> list[tuple[str, int]]:
    """Find fuzzy matches for query in candidates. Returns [(candidate, score)]."""
    q = normalize(query)
    matches = []
    for c in candidates:
        cn = normalize(c)
        # Exact match
        if q == cn:
            matches.append((c, 100))
            continue
        # Contains: query is substring of candidate
        if q in cn and len(q) >= 5:
            matches.append((c, 95))
            continue
        # Reverse: candidate is substring of query
        if cn in q and len(cn) >= len(q) * 0.6:
            matches.append((c, 90))
            continue
        # Fuzzy
        score = fuzz.token_sort_ratio(q, cn)
        if score >= threshold:
            matches.append((c, score))
    return sorted(matches, key=lambda x: -x[1])


def match_entry(name: str, packages: dict[str, list[str]], manual_index: list[str],
                home: list[str], appdata_entries: list[str]) -> dict:
    """Match a name against all known sources. Returns match result dict."""
    result = {
        "query": name,
        "packages": [],
        "manual": [],
        "home": [],
        "appdata": [],
        "verdict": "unknown",
    }

    # Flatten all package names with source tags
    all_pkg_names = []
    for pm, names in packages.items():
        for n in names:
            all_pkg_names.append(f"{pm}: {n}")

    result["packages"] = fuzzy_match(name, [n.split(": ", 1)[1] for n in all_pkg_names])
    # Re-attach source
    pkg_matches = []
    for matched_name, score in result["packages"]:
        for full in all_pkg_names:
            if full.endswith(f": {matched_name}"):
                pkg_matches.append((full, score))
                break
    result["packages"] = pkg_matches

    result["manual"] = fuzzy_match(name, manual_index)
    result["home"] = fuzzy_match(name, home)
    result["appdata"] = fuzzy_match(name, appdata_entries)

    # Filter out self-matches from scan file results
    result["home"] = [(m, s) for m, s in result["home"] if m != name]
    result["appdata"] = [(m, s) for m, s in result["appdata"] if m != name]

    # Determine verdict
    has_pkg = result["packages"] and result["packages"][0][1] >= 80
    has_man = result["manual"] and result["manual"][0][1] >= 80
    has_home = result["home"] and result["home"][0][1] >= 80
    has_app = result["appdata"] and result["appdata"][0][1] >= 80

    if has_pkg:
        result["verdict"] = "active (package manager)"
    elif has_man:
        result["verdict"] = "active (manual install)"
    elif has_home or has_app:
        result["verdict"] = "stale (not in package manager)"
    else:
        result["verdict"] = "unknown"

    return result
