#!/usr/bin/env python3
"""
tools/export_repo_indexes.py

Exports lightweight, agent-friendly repo "indexes" WITHOUT exporting source code.
Outputs YAML (no external deps). Safe defaults: skip binaries, skip huge files, skip junk dirs.

Usage:
  python tools/export_repo_indexes.py \
    --repo-root . \
    --output-dir ./handoff_indexes \
    --include-metadata \
    --include-file-map \
    --include-entrypoints \
    --include-integrations \
    --include-env-flags \
    --include-deltas
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# -----------------------------
# Config / defaults
# -----------------------------

DEFAULT_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".DS_Store",
    ".idea",
    ".vscode",
}
DEFAULT_IGNORE_FILES = {
    ".DS_Store",
}
TEXT_EXT_ALLOWLIST = {
    ".py",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
    ".example",
    ".template",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".dockerfile",
    "Dockerfile",
}
MAX_FILE_BYTES_DEFAULT = 1_250_000  # 1.25MB per file scan cap
MAX_LINES_PER_FILE_DEFAULT = 2_000  # cap reading per file
TREE_DEPTH_DEFAULT = 6

# Heuristic patterns (fast, good enough)
RE_FASTAPI_APP = re.compile(r"\bapp\s*=\s*FastAPI\(", re.IGNORECASE)
RE_APIRouter = re.compile(r"\bAPIRouter\(", re.IGNORECASE)
RE_INCLUDE_ROUTER = re.compile(r"\binclude_router\(", re.IGNORECASE)
RE_UVICORN_RUN = re.compile(r"\buvicorn\b.*\b([a-zA-Z0-9_./]+):app\b")
RE_MAIN_GUARD = re.compile(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:')
RE_OS_GETENV = re.compile(r"os\.getenv\(\s*[\'\"]([A-Z0-9_]+)[\'\"]")
RE_ENVIRON_GET = re.compile(r"os\.environ\.get\(\s*[\'\"]([A-Z0-9_]+)[\'\"]")
RE_ENV_BRACKET = re.compile(r"os\.environ\[\s*[\'\"]([A-Z0-9_]+)[\'\"]\s*\]")
RE_DOTENV_LOOKUP = re.compile(r"\bdotenv\b|\bload_dotenv\b", re.IGNORECASE)

# Integration signals
INTEGRATION_PATTERNS = {
    "slack": [
        re.compile(r"\bslack\b", re.IGNORECASE),
        re.compile(
            r"\bxox[baprs]-", re.IGNORECASE
        ),  # token prefix (won't capture full token)
        re.compile(r"SLACK_[A-Z0-9_]+"),
    ],
    "twilio": [
        re.compile(r"\btwilio\b", re.IGNORECASE),
        re.compile(r"TWILIO_[A-Z0-9_]+"),
    ],
    "waba": [
        re.compile(r"\bwaba\b", re.IGNORECASE),
        re.compile(r"WHATSAPP_[A-Z0-9_]+|WABA_[A-Z0-9_]+"),
    ],
    "google": [
        re.compile(
            r"\bgoogleapiclient\b|\bgoogle\.oauth2\b|\bgspread\b|\bgmail\b|\bcalendar\b",
            re.IGNORECASE,
        ),
        re.compile(r"GOOGLE_[A-Z0-9_]+"),
    ],
    "openai": [
        re.compile(r"\bopenai\b", re.IGNORECASE),
        re.compile(r"OPENAI_API_KEY"),
    ],
    "email": [
        re.compile(r"\bsmtplib\b|\bimaplib\b|\bgmail\b", re.IGNORECASE),
        re.compile(r"EMAIL_[A-Z0-9_]+"),
    ],
    "playwright": [
        re.compile(r"\bplaywright\b", re.IGNORECASE),
    ],
    "websocket": [
        re.compile(r"\bwebsocket\b|\bwebsockets\b", re.IGNORECASE),
        re.compile(r"\bws://|\bwss://", re.IGNORECASE),
    ],
    "postgres": [
        re.compile(r"\bpsycopg\b|\bpsycopg2\b", re.IGNORECASE),
        re.compile(r"POSTGRES|PGHOST|PGPORT|PGUSER|PGPASSWORD|PGDATABASE"),
    ],
    "redis": [
        re.compile(r"\bredis\b", re.IGNORECASE),
        re.compile(r"REDIS_[A-Z0-9_]+"),
    ],
}

# -----------------------------
# Minimal YAML writer (no deps)
# -----------------------------


def _yaml_escape(s: str) -> str:
    # Quote if unsafe
    if (
        s == ""
        or any(c in s for c in [":", "{", "}", "[", "]", "#", "\n", "\r", "\t"])
        or s.strip() != s
    ):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if s.lower() in {"true", "false", "null", "~"}:
        return '"' + s + '"'
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        return '"' + s + '"'
    return s


def _to_yaml(obj: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, (int, float)):
        return str(obj)
    if isinstance(obj, str):
        return _yaml_escape(obj)
    if isinstance(obj, list):
        if not obj:
            return "[]"
        lines = []
        for item in obj:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}- {_to_yaml(item, indent + 1).lstrip()}")
            else:
                lines.append(f"{pad}- {_to_yaml(item, 0)}")
        return "\n".join(lines)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = []
        for k in sorted(obj.keys(), key=lambda x: str(x)):
            v = obj[k]
            key = _yaml_escape(str(k))
            if isinstance(v, (dict, list)):
                rendered = _to_yaml(v, indent + 1)
                if "\n" in rendered:
                    lines.append(f"{pad}{key}:")
                    lines.append(rendered)
                else:
                    lines.append(f"{pad}{key}: {rendered}")
            else:
                lines.append(f"{pad}{key}: {_to_yaml(v, 0)}")
        return "\n".join(lines)
    # Fallback: string repr
    return _yaml_escape(str(obj))


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _to_yaml(data, indent=0) + "\n"
    path.write_text(content, encoding="utf-8")


# -----------------------------
# Utilities
# -----------------------------


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def is_probably_binary(path: Path) -> bool:
    try:
        raw = path.read_bytes()[:2048]
    except Exception:
        return True
    if b"\x00" in raw:
        return True
    # If mostly non-text bytes, treat as binary
    text_chars = sum(1 for c in raw if 9 <= c <= 13 or 32 <= c <= 126)
    return (len(raw) > 0) and (text_chars / len(raw) < 0.70)


def should_scan_file(path: Path, max_bytes: int) -> bool:
    if path.name in DEFAULT_IGNORE_FILES:
        return False
    if path.is_symlink():
        return False
    try:
        size = path.stat().st_size
    except Exception:
        return False
    if size == 0:
        return False
    if size > max_bytes:
        return False
    ext = path.suffix.lower()
    if path.name == "Dockerfile":
        return True
    if ext in TEXT_EXT_ALLOWLIST:
        return True
    # allow "requirements.txt" etc
    if path.name.startswith("requirements") and path.name.endswith(".txt"):
        return True
    return False


def iter_files(repo_root: Path, ignore_dirs: set[str]) -> list[Path]:
    files: list[Path] = []
    for root, dirs, filenames in os.walk(repo_root):
        root_p = Path(root)
        # prune ignored dirs
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for fn in filenames:
            p = root_p / fn
            if p.name in DEFAULT_IGNORE_FILES:
                continue
            files.append(p)
    return files


def relpath(repo_root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(repo_root))
    except Exception:
        return str(p)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


# -----------------------------
# Index builders
# -----------------------------


def build_metadata(repo_root: Path, all_files: list[Path]) -> dict[str, Any]:
    py_files = [p for p in all_files if p.suffix.lower() == ".py"]
    md_files = [p for p in all_files if p.suffix.lower() == ".md"]
    has_docker = any(
        p.name == "docker-compose.yml" or p.name == "Dockerfile" for p in all_files
    )
    has_requirements = any(
        p.name.startswith("requirements") and p.name.endswith(".txt") for p in all_files
    )

    # crude module tree detection at top-level
    top_dirs = sorted(
        {
            p.parts[0]
            for p in [Path(relpath(repo_root, f)) for f in all_files]
            if len(p.parts) > 1
        }
    )
    return {
        "export": {
            "generated_at": now_iso(),
            "repo_root": str(repo_root.resolve()),
            "file_count": len(all_files),
        },
        "signals": {
            "python_files": len(py_files),
            "markdown_files": len(md_files),
            "has_docker": has_docker,
            "has_requirements_txt": has_requirements,
        },
        "top_level_dirs": top_dirs,
    }


def build_tree_map(
    repo_root: Path, all_files: list[Path], depth: int
) -> dict[str, Any]:
    """
    Build a depth-limited nested dict of directories -> files (names only).
    This is NOT code export; just structure.
    """
    tree: dict[str, Any] = {}

    def insert(parts: list[str]) -> None:
        node = tree
        for i, part in enumerate(parts):
            if i >= depth:
                break
            is_last = i == len(parts) - 1
            if is_last:
                node.setdefault("_files", []).append(part)
            else:
                node = node.setdefault(part, {})

    for f in all_files:
        rp = Path(relpath(repo_root, f))
        parts = list(rp.parts)
        if not parts:
            continue
        insert(parts)

    # sort _files
    def sort_node(n: Any) -> None:
        if isinstance(n, dict):
            if "_files" in n and isinstance(n["_files"], list):
                n["_files"] = sorted(set(n["_files"]))
            for k, v in n.items():
                if k == "_files":
                    continue
                sort_node(v)

    sort_node(tree)
    return {"tree_depth": depth, "tree": tree}


def scan_text_files(
    repo_root: Path,
    files: list[Path],
    max_bytes: int,
    max_lines: int,
) -> list[tuple[str, list[str]]]:
    """
    Returns list of (relative_path, lines) for safe-to-scan text files.
    """
    out: list[tuple[str, list[str]]] = []
    for p in files:
        if not should_scan_file(p, max_bytes):
            continue
        if is_probably_binary(p):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lines = text.splitlines()[:max_lines]
        out.append((relpath(repo_root, p), lines))
    return out


def build_env_flags(scanned: list[tuple[str, list[str]]]) -> dict[str, Any]:
    hits: dict[str, dict[str, Any]] = {}
    for rpath, lines in scanned:
        joined = "\n".join(lines)
        for re_pat in (RE_OS_GETENV, RE_ENVIRON_GET, RE_ENV_BRACKET):
            for m in re_pat.finditer(joined):
                key = m.group(1)
                rec = hits.setdefault(key, {"files": set(), "patterns": set()})
                rec["files"].add(rpath)
                rec["patterns"].add(re_pat.pattern)

        # heuristic: dotenv usage
        if RE_DOTENV_LOOKUP.search(joined):
            rec = hits.setdefault("DOTENV_USAGE", {"files": set(), "patterns": set()})
            rec["files"].add(rpath)
            rec["patterns"].add("dotenv/load_dotenv")

    # normalize
    env_vars = []
    for k in sorted(hits.keys()):
        env_vars.append(
            {
                "name": k,
                "files": sorted(hits[k]["files"]),
                "signals": sorted(hits[k]["patterns"]),
            }
        )

    # lightweight required/optional guess: required if used in auth or startup paths
    required = []
    optional = []
    for item in env_vars:
        name = item["name"]
        files = " ".join(item["files"])
        if name in {"OPENAI_API_KEY", "L9_EXECUTOR_API_KEY"}:
            required.append(name)
        elif any(x in files for x in ["auth", "server", "startup", "server_memory"]):
            # guess required but mark as "suspected"
            optional.append(name)
        else:
            optional.append(name)

    return {
        "env_vars": env_vars,
        "required_minimum": sorted(set(required)),
        "optional_or_contextual": sorted(set(optional) - set(required)),
    }


def build_entrypoints(scanned: list[tuple[str, list[str]]]) -> dict[str, Any]:
    entrypoints: list[dict[str, Any]] = []
    uvicorn_candidates: list[dict[str, Any]] = []
    fastapi_apps: list[dict[str, Any]] = []
    main_guards: list[str] = []

    for rpath, lines in scanned:
        text = "\n".join(lines)
        if RE_FASTAPI_APP.search(text):
            fastapi_apps.append({"file": rpath})
        if RE_MAIN_GUARD.search(text):
            main_guards.append(rpath)
        for m in RE_UVICORN_RUN.finditer(text):
            uvicorn_candidates.append({"file": rpath, "match": m.group(0)})

    # Expand with common "run commands" in README-like files
    run_cmds: list[dict[str, Any]] = []
    for rpath, lines in scanned:
        if not (rpath.lower().endswith(".md") or "readme" in rpath.lower()):
            continue
        for ln in lines:
            if (
                "uvicorn " in ln
                or "python -m " in ln
                or ("python " in ln and "api." in ln)
            ):
                run_cmds.append({"file": rpath, "line": ln.strip()})

    entrypoints.append(
        {
            "fastapi_apps": fastapi_apps,
            "uvicorn_mentions": uvicorn_candidates,
            "main_guard_files": sorted(set(main_guards)),
            "run_command_hints": run_cmds[:200],
        }
    )
    return {"entrypoints": entrypoints}


def build_integrations(scanned: list[tuple[str, list[str]]]) -> dict[str, Any]:
    found: dict[str, dict[str, Any]] = {}
    for rpath, lines in scanned:
        text = "\n".join(lines)
        for name, patterns in INTEGRATION_PATTERNS.items():
            for pat in patterns:
                if pat.search(text):
                    rec = found.setdefault(name, {"files": set(), "signals": set()})
                    rec["files"].add(rpath)
                    rec["signals"].add(pat.pattern)

    integrations = []
    for name in sorted(found.keys()):
        integrations.append(
            {
                "name": name,
                "files": sorted(found[name]["files"]),
                "signals": sorted(found[name]["signals"])[:50],
            }
        )

    # Also detect FastAPI routers (helpful for Slack/Twilio/etc)
    routers = []
    for rpath, lines in scanned:
        text = "\n".join(lines)
        if RE_APIRouter.search(text) or RE_INCLUDE_ROUTER.search(text):
            routers.append(rpath)

    return {
        "integrations": integrations,
        "fastapi_router_files": sorted(set(routers)),
    }


def build_file_map(repo_root: Path, all_files: list[Path]) -> dict[str, Any]:
    """
    File map = paths + lightweight role hints based on filename patterns.
    """
    role_rules = [
        (re.compile(r"server_memory\.py$"), "fastapi_memory_api_entry"),
        (re.compile(r"webhook_.*\.py$"), "webhook_router"),
        (re.compile(r"auth\.py$"), "auth_layer"),
        (re.compile(r"db\.py$"), "database_layer"),
        (re.compile(r"router\.py$"), "api_router"),
        (re.compile(r"agent\.py$"), "agent_entry"),
        (re.compile(r"websocket_.*\.py$"), "websocket_client_or_server"),
        (re.compile(r"reverse_tunnel.*\.sh$"), "reverse_tunnel_script"),
        (re.compile(r"install_.*\.sh$"), "install_script"),
        (re.compile(r".*docker-compose\.yml$"), "docker_compose"),
        (re.compile(r"requirements.*\.txt$"), "python_requirements"),
    ]

    items: list[dict[str, Any]] = []
    for p in all_files:
        rp = relpath(repo_root, p)
        # only map "interesting" files to keep it light
        if not (
            rp.endswith(".py")
            or rp.endswith(".yml")
            or rp.endswith(".yaml")
            or rp.endswith(".md")
            or rp.endswith(".sh")
            or rp.endswith(".txt")
            or rp.endswith(".env")
            or "Dockerfile" in rp
            or "docker-compose" in rp
        ):
            continue

        hint = None
        for pat, role in role_rules:
            if pat.search(rp):
                hint = role
                break

        items.append(
            {
                "path": rp,
                "role_hint": hint or "unknown",
            }
        )

    return {
        "file_count_mapped": len(items),
        "files": items[:5000],  # hard cap
    }


def build_deltas(repo_root: Path, all_files: list[Path]) -> dict[str, Any]:
    """
    "Deltas" here = structural drift risks, not git diffs.
    Main: duplicate module trees (api/, memory/, world_model/ duplicated under l9/ etc.)
    """
    rels = [Path(relpath(repo_root, f)) for f in all_files]
    top_dirs = {p.parts[0] for p in rels if len(p.parts) > 1}

    # detect duplicate trees: e.g. api/ and l9/api/ both exist
    dup_pairs = []
    if "l9" in top_dirs:
        second_level = {
            p.parts[1] for p in rels if len(p.parts) > 2 and p.parts[0] == "l9"
        }
        for d in sorted(second_level):
            if d in top_dirs:
                dup_pairs.append({"primary": f"{d}/", "mirror": f"l9/{d}/"})

    risks = []
    if dup_pairs:
        risks.append(
            {
                "type": "duplicate_module_trees",
                "pairs": dup_pairs,
                "risk": "Ambiguous imports/edits: agents and humans may patch the wrong copy; runtime may load the other.",
                "mitigation": [
                    "Declare canonical tree in metadata (e.g., api/ is canonical; l9/api/ is deprecated).",
                    "Add a policy: forbid edits in deprecated trees; enforce via lint or code review.",
                    "Optionally collapse into one tree later.",
                ],
            }
        )

    # also detect multiple "server_memory.py" occurrences
    sm = [str(p) for p in rels if p.name == "server_memory.py"]
    if len(sm) > 1:
        risks.append(
            {
                "type": "duplicate_entrypoint_filenames",
                "files": sm,
                "risk": "Multiple apparent entrypoints with same name increases mispatch probability.",
            }
        )

    return {"drift_risks": risks}


def write_manifest(
    out_dir: Path, produced: list[str], args: argparse.Namespace
) -> None:
    data = {
        "manifest": {
            "generated_at": now_iso(),
            "python": sys.version.split()[0],
            "command": " ".join(map(str, sys.argv)),
            "output_dir": str(out_dir.resolve()),
            "produced_files": produced,
        },
        "flags": {
            k: bool(getattr(args, k))
            for k in [
                "include_metadata",
                "include_file_map",
                "include_entrypoints",
                "include_integrations",
                "include_env_flags",
                "include_deltas",
            ]
        },
    }
    write_yaml(out_dir / "export_manifest.yaml", data)


# -----------------------------
# Main
# -----------------------------


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True, help="Repo root (.)")
    ap.add_argument("--output-dir", required=True, help="Where to write indexes")
    ap.add_argument("--tree-depth", type=int, default=TREE_DEPTH_DEFAULT)
    ap.add_argument("--max-file-bytes", type=int, default=MAX_FILE_BYTES_DEFAULT)
    ap.add_argument(
        "--max-lines-per-file", type=int, default=MAX_LINES_PER_FILE_DEFAULT
    )
    ap.add_argument(
        "--ignore-dir",
        action="append",
        default=[],
        help="Extra dir names to ignore (repeatable)",
    )

    ap.add_argument("--include-metadata", action="store_true")
    ap.add_argument("--include-file-map", action="store_true")
    ap.add_argument("--include-entrypoints", action="store_true")
    ap.add_argument("--include-integrations", action="store_true")
    ap.add_argument("--include-env-flags", action="store_true")
    ap.add_argument("--include-deltas", action="store_true")

    return ap.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ignore_dirs = set(DEFAULT_IGNORE_DIRS)
    ignore_dirs.update(args.ignore_dir)

    all_files = iter_files(repo_root, ignore_dirs)
    produced: list[str] = []

    # Prepare scanned text lines ONCE (for the include-* features that need it)
    # (We scan only safe text-like files)
    scanned = scan_text_files(
        repo_root=repo_root,
        files=all_files,
        max_bytes=args.max_file_bytes,
        max_lines=args.max_lines_per_file,
    )

    if args.include_metadata:
        data = build_metadata(repo_root, all_files)
        write_yaml(out_dir / "repo_metadata.yaml", data)
        produced.append("repo_metadata.yaml")

    # Tree is part of file-map feature in spirit, but keep it separate and optional:
    if args.include_file_map:
        fm = build_file_map(repo_root, all_files)
        write_yaml(out_dir / "repo_file_map.yaml", fm)
        produced.append("repo_file_map.yaml")

        tm = build_tree_map(repo_root, all_files, depth=args.tree_depth)
        write_yaml(out_dir / "repo_tree.yaml", tm)
        produced.append("repo_tree.yaml")

    if args.include_entrypoints:
        ep = build_entrypoints(scanned)
        write_yaml(out_dir / "entrypoints.yaml", ep)
        produced.append("entrypoints.yaml")

    if args.include_integrations:
        integ = build_integrations(scanned)
        write_yaml(out_dir / "integrations.yaml", integ)
        produced.append("integrations.yaml")

    if args.include_env_flags:
        env = build_env_flags(scanned)
        write_yaml(out_dir / "env_flags.yaml", env)
        produced.append("env_flags.yaml")

    if args.include_deltas:
        d = build_deltas(repo_root, all_files)
        write_yaml(out_dir / "deltas.yaml", d)
        produced.append("deltas.yaml")

    write_manifest(out_dir, produced, args)
    produced.append("export_manifest.yaml")

    # Print a clean terminal summary (stdout)
    print(f"OK: exported {len(produced)} files to {out_dir}")  # noqa: ADR-0019
    for name in produced:
        p = out_dir / name
        try:
            sz = p.stat().st_size
        except Exception:
            sz = -1
        print(f" - {name} ({sz} bytes)")  # noqa: ADR-0019
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
