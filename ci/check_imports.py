#!/usr/bin/env python3
"""
CI check for missing imports in Python files.

Uses AST parsing to detect stdlib module usage without imports.
Checks for specific method/attribute patterns unique to each module.

Usage:
    python ci/check_imports.py
    python ci/check_imports.py path/to/file.py
    python ci/check_imports.py --all  # Check all patterns (slower)

Exit codes:
    0 - All checks passed
    1 - Missing imports found
"""

from __future__ import annotations

import structlog

# ============================================================================

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "Check Imports",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:21:50Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_imports",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import ast
import sys
from pathlib import Path

L9_ROOT = Path(__file__).parent.parent

# Module -> (specific_attributes that confirm it's the stdlib module, import_fix)
# Only attributes that are UNIQUE to the stdlib module (not common attribute names)
STDLIB_PATTERNS = {
    # datetime module
    "timezone": ({"utc"}, "from datetime import timezone"),
    "timedelta": (
        {"days", "seconds", "microseconds", "total_seconds"},
        "from datetime import timedelta",
    ),
    # Core stdlib with unique attributes
    "asyncio": (
        {
            "run",
            "gather",
            "create_task",
            "sleep",
            "wait",
            "wait_for",
            "Queue",
            "Lock",
            "Event",
            "Semaphore",
            "get_event_loop",
            "new_event_loop",
            "all_tasks",
            "current_task",
        },
        "import asyncio",
    ),
    "logging": (
        {
            "getLogger",
            "basicConfig",
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "StreamHandler",
            "FileHandler",
            "Formatter",
        },
        "import logging",
    ),
    "json": (
        {
            "dumps",
            "loads",
            "dump",
            "load",
            "JSONEncoder",
            "JSONDecoder",
            "JSONDecodeError",
        },
        "import json",
    ),
    "re": (
        {
            "match",
            "search",
            "compile",
            "sub",
            "findall",
            "split",
            "fullmatch",
            "subn",
            "escape",
            "Pattern",
            "IGNORECASE",
            "MULTILINE",
            "DOTALL",
        },
        "import re",
    ),
    "os": (
        {
            "environ",
            "getenv",
            "makedirs",
            "listdir",
            "remove",
            "rmdir",
            "rename",
            "getcwd",
            "chdir",
            "path",
            "walk",
            "sep",
            "linesep",
        },
        "import os",
    ),
    "sys": (
        {
            "exit",
            "argv",
            "path",
            "stdout",
            "stderr",
            "stdin",
            "exc_info",
            "version",
            "version_info",
            "modules",
            "executable",
        },
        "import sys",
    ),
    # Collections and utilities
    "collections": (
        {"defaultdict", "Counter", "OrderedDict", "namedtuple", "deque", "ChainMap"},
        "import collections",
    ),
    "functools": (
        {
            "wraps",
            "partial",
            "lru_cache",
            "cache",
            "cached_property",
            "reduce",
            "singledispatch",
        },
        "import functools",
    ),
    "itertools": (
        {
            "chain",
            "groupby",
            "combinations",
            "permutations",
            "product",
            "cycle",
            "repeat",
            "islice",
            "takewhile",
            "dropwhile",
            "starmap",
        },
        "import itertools",
    ),
    "operator": (
        {"itemgetter", "attrgetter", "methodcaller", "add", "mul", "sub"},
        "import operator",
    ),
    # Type-related
    "typing": (
        {
            "Optional",
            "List",
            "Dict",
            "Set",
            "Tuple",
            "Union",
            "Any",
            "Callable",
            "TypeVar",
            "Generic",
            "Protocol",
            "Literal",
            "Final",
            "ClassVar",
            "TYPE_CHECKING",
        },
        "import typing",
    ),
    "dataclasses": (
        {"dataclass", "field", "asdict", "astuple", "fields", "replace"},
        "import dataclasses",
    ),
    "enum": ({"Enum", "IntEnum", "Flag", "auto", "unique"}, "import enum"),
    "abc": ({"ABC", "abstractmethod", "abstractproperty", "ABCMeta"}, "import abc"),
    # Common utilities
    "uuid": (
        {"uuid4", "uuid1", "uuid5", "UUID", "NAMESPACE_DNS", "NAMESPACE_URL"},
        "import uuid",
    ),
    "hashlib": (
        {"md5", "sha256", "sha1", "sha512", "sha384", "new", "pbkdf2_hmac"},
        "import hashlib",
    ),
    "base64": (
        {
            "b64encode",
            "b64decode",
            "urlsafe_b64encode",
            "urlsafe_b64decode",
            "encodebytes",
            "decodebytes",
        },
        "import base64",
    ),
    "copy": ({"deepcopy", "copy"}, "import copy"),
    "pickle": (
        {"dump", "dumps", "load", "loads", "Pickler", "Unpickler"},
        "import pickle",
    ),
    # Error handling and introspection
    "traceback": (
        {
            "format_exc",
            "print_exc",
            "format_exception",
            "extract_tb",
            "format_tb",
            "print_tb",
        },
        "import traceback",
    ),
    "inspect": (
        {
            "signature",
            "getmembers",
            "isclass",
            "isfunction",
            "ismethod",
            "getfile",
            "getsource",
            "currentframe",
            "stack",
        },
        "import inspect",
    ),
    "warnings": (
        {"warn", "filterwarnings", "catch_warnings", "simplefilter"},
        "import warnings",
    ),
    # Context and async utilities
    "contextlib": (
        {
            "asynccontextmanager",
            "contextmanager",
            "suppress",
            "redirect_stdout",
            "redirect_stderr",
            "ExitStack",
            "AsyncExitStack",
            "nullcontext",
        },
        "import contextlib",
    ),
    # IO and paths
    "pathlib": (
        {"Path", "PurePath", "PosixPath", "WindowsPath"},
        "from pathlib import Path",
    ),
    "io": (
        {"StringIO", "BytesIO", "TextIOWrapper", "BufferedReader", "BufferedWriter"},
        "import io",
    ),
    "tempfile": (
        {"NamedTemporaryFile", "TemporaryDirectory", "mktemp", "mkdtemp", "gettempdir"},
        "import tempfile",
    ),
    "shutil": (
        {"copy", "copy2", "copytree", "rmtree", "move", "which", "disk_usage"},
        "import shutil",
    ),
    "glob": ({"glob", "iglob"}, "import glob"),
    # Time and dates
    "time": (
        {
            "sleep",
            "time",
            "perf_counter",
            "monotonic",
            "strftime",
            "strptime",
            "localtime",
            "gmtime",
        },
        "import time",
    ),
    "calendar": (
        {"monthrange", "isleap", "weekday", "month_name", "day_name"},
        "import calendar",
    ),
    # Threading and multiprocessing
    "threading": (
        {
            "Thread",
            "Lock",
            "RLock",
            "Event",
            "Condition",
            "Semaphore",
            "Barrier",
            "Timer",
            "current_thread",
            "active_count",
        },
        "import threading",
    ),
    "multiprocessing": (
        {"Process", "Pool", "Queue", "Pipe", "Manager", "cpu_count", "current_process"},
        "import multiprocessing",
    ),
    "concurrent": (
        {
            "futures",
        },
        "import concurrent.futures",
    ),
    # Network
    "socket": (
        {"socket", "AF_INET", "SOCK_STREAM", "gethostname", "gethostbyname"},
        "import socket",
    ),
    "urllib": ({"parse", "request", "error"}, "import urllib"),
    "http": ({"client", "server", "HTTPStatus"}, "import http"),
    # Data formats
    "csv": (
        {"reader", "writer", "DictReader", "DictWriter", "QUOTE_ALL", "QUOTE_MINIMAL"},
        "import csv",
    ),
    "xml": (
        {
            "etree",
        },
        "import xml.etree.ElementTree",
    ),
    # Math and random
    "math": (
        {
            "sqrt",
            "ceil",
            "floor",
            "log",
            "log10",
            "exp",
            "sin",
            "cos",
            "tan",
            "pi",
            "e",
            "inf",
            "nan",
            "isnan",
            "isinf",
        },
        "import math",
    ),
    "random": (
        {
            "randint",
            "choice",
            "shuffle",
            "sample",
            "random",
            "uniform",
            "randrange",
            "seed",
            "choices",
        },
        "import random",
    ),
    "statistics": (
        {"mean", "median", "mode", "stdev", "variance"},
        "import statistics",
    ),
    "decimal": (
        {"Decimal", "ROUND_HALF_UP", "ROUND_DOWN", "getcontext"},
        "import decimal",
    ),
    "fractions": (
        {
            "Fraction",
        },
        "import fractions",
    ),
    # String utilities
    "string": (
        {
            "ascii_letters",
            "ascii_lowercase",
            "ascii_uppercase",
            "digits",
            "punctuation",
            "Template",
        },
        "import string",
    ),
    "textwrap": ({"wrap", "fill", "dedent", "indent", "shorten"}, "import textwrap"),
    "difflib": (
        {"SequenceMatcher", "unified_diff", "ndiff", "get_close_matches"},
        "import difflib",
    ),
    # Compression
    "gzip": ({"open", "compress", "decompress", "GzipFile"}, "import gzip"),
    "zipfile": (
        {"ZipFile", "is_zipfile", "ZIP_DEFLATED", "ZIP_STORED"},
        "import zipfile",
    ),
    "tarfile": ({"open", "TarFile", "is_tarfile"}, "import tarfile"),
    # Subprocess
    "subprocess": (
        {
            "run",
            "Popen",
            "PIPE",
            "STDOUT",
            "DEVNULL",
            "call",
            "check_call",
            "check_output",
            "CalledProcessError",
        },
        "import subprocess",
    ),
    # Argument parsing
    "argparse": (
        {"ArgumentParser", "Namespace", "FileType", "Action"},
        "import argparse",
    ),
    # Config parsing
    "configparser": (
        {"ConfigParser", "RawConfigParser", "SafeConfigParser"},
        "import configparser",
    ),
    # Secrets and security
    "secrets": (
        {"token_bytes", "token_hex", "token_urlsafe", "choice", "randbelow"},
        "import secrets",
    ),
    "hmac": ({"new", "compare_digest", "digest"}, "import hmac"),
    # Struct and binary
    "struct": ({"pack", "unpack", "calcsize", "Struct"}, "import struct"),
    # Python internals
    "types": (
        {
            "SimpleNamespace",
            "FunctionType",
            "MethodType",
            "ModuleType",
            "GeneratorType",
            "CoroutineType",
        },
        "import types",
    ),
    "typing_extensions": (
        {"TypedDict", "Annotated", "ParamSpec", "Self", "NotRequired", "Required"},
        "import typing_extensions",
    ),
    # pprint
    "pprint": ({"pprint", "pformat", "PrettyPrinter"}, "import pprint"),
}

# Critical patterns always checked (fast)
CRITICAL_PATTERNS = {"timezone", "timedelta", "asyncio"}

# Extended patterns (--all flag)
EXTENDED_PATTERNS = set(STDLIB_PATTERNS.keys()) - CRITICAL_PATTERNS

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    "current_work",
    "_archived",
    ".backup",
    "igor",
    "codegen",
    ".dora",
    ".github",
}


def get_imported_names(tree: ast.AST) -> set[str]:
    """Extract all imported names from AST."""
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imported.add(name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
            for alias in node.names:
                imported.add(alias.asname or alias.name)
    return imported


def get_module_attr_usage(tree: ast.AST) -> dict[str, set[str]]:
    """
    Find all module.attribute patterns in the AST.

    Returns dict of module_name -> set of attributes accessed.
    """
    usage: dict[str, set[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                module_name = node.value.id
                attr_name = node.attr
                if module_name not in usage:
                    usage[module_name] = set()
                usage[module_name].add(attr_name)

    return usage


def check_file(filepath: Path, patterns: set[str]) -> list[tuple[str, str, set[str]]]:
    """
    Check a file for missing imports.

    Returns list of (module_name, fix, attrs_used) tuples.
    """
    try:
        content = filepath.read_text()
        tree = ast.parse(content)
    except Exception:
        return []

    imported = get_imported_names(tree)
    usage = get_module_attr_usage(tree)

    issues = []
    for module_name in patterns:
        if module_name not in STDLIB_PATTERNS:
            continue

        unique_attrs, fix = STDLIB_PATTERNS[module_name]

        # Skip if already imported
        if module_name in imported:
            continue

        # Check if module is used with unique attributes
        if module_name in usage:
            attrs_used = usage[module_name]
            # Only flag if ANY of the unique attributes are used
            matching_attrs = attrs_used & unique_attrs
            if matching_attrs:
                issues.append((module_name, fix, matching_attrs))

    return issues


def main() -> int:
    """Run import checks on L9 codebase."""
    parser = argparse.ArgumentParser(description="Check for missing imports")
    parser.add_argument(
        "--all", "-a", action="store_true", help="Check all patterns (slower)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show summary")
    parser.add_argument(
        "--list", "-l", action="store_true", help="List available patterns"
    )
    parser.add_argument(
        "files", nargs="*", help="Specific files to check (default: all)"
    )
    args = parser.parse_args()

    if args.list:
        logger.info("available patterns:\n")
        logger.info("critical (always checked):")
        for p in sorted(CRITICAL_PATTERNS):
            _, fix = STDLIB_PATTERNS[p]
            logger.info("  p -> fix", p=p, fix=fix)
        logger.info("\nextended (--all flag, {len(extended_patterns)} patterns):")
        for p in sorted(EXTENDED_PATTERNS):
            _, fix = STDLIB_PATTERNS[p]
            logger.info("  p -> fix", p=p, fix=fix)
        return 0

    patterns = CRITICAL_PATTERNS if not args.all else set(STDLIB_PATTERNS.keys())

    if args.files:
        files = [Path(f) for f in args.files if f.endswith(".py")]
    else:
        files = [
            f
            for f in L9_ROOT.rglob("*.py")
            if f.is_file() and not any(d in f.parts for d in SKIP_DIRS)
        ]

    all_issues: list[tuple[Path, str, str, set[str]]] = []

    for filepath in sorted(files):
        issues = check_file(filepath, patterns)
        for module_name, fix, attrs in issues:
            all_issues.append((filepath, module_name, fix, attrs))

    if all_issues:
        logger.info("❌ missing imports found ({len(all_issues)}):\n")
        for filepath, module_name, fix, attrs in all_issues:
            rel = (
                filepath.relative_to(L9_ROOT)
                if filepath.is_relative_to(L9_ROOT)
                else filepath
            )
            attrs_str = ", ".join(sorted(attrs)[:3])
            if len(attrs) > 3:
                attrs_str += f", ... ({len(attrs)} total)"
            logger.info("  rel", rel=rel)
            logger.info(
                "    uses: module name.{{attrs str}}",
                module_name=module_name,
                attrs_str=attrs_str,
            )
            logger.info("    fix:  fix\n", fix=fix)

        return 1

    if args.verbose:
        print(
            f"✅ Checked {len(files)} files with {len(patterns)} patterns - no missing imports"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-019",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "ast",
        "caching",
        "ci",
        "cli",
        "debugging",
        "event-driven",
        "filesystem",
        "operations",
        "queue",
        "security",
    ],
    "keywords": ["check", "imported", "imports", "module", "names", "usage"],
    "business_value": "Utility module for check imports",
    "last_modified": "2026-01-31T22:21:50Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
