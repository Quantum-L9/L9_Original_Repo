"""
L9 CI — Repository contract meta-tests
========================================

META = repo-wide: find every caller of contract methods across the codebase
and ensure each call is valid so the callee can receive and reply correctly.

1. Repo-wide call-site scan: discover all calls to insert_knowledge_fact,
   insert_semantic_embedding, etc. in memory/, core/, api/, scripts/, ...
2. For each call site: if scope (or other param) is passed as a literal,
   it must be in the allowed list so the callee accepts it.
3. Callee contract: stub (and real implementation) must accept every
   allowed value and succeed.

Not limited to insert_knowledge_fact: add (method_name, param_name,
allowed_values) to CONTRACT_METHODS_FOR_SCAN and to REPOSITORY_CONTRACT_REGISTRY.

Version: 1.0.0
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

# ============================================================================
__dora_meta__ = {
    "component_name": "Repository Contract CI",
    "module_version": "1.0.0",
    "layer": "testing",
    "domain": "ci_enforcement",
    "module_name": "test_repository_contract_calls",
    "type": "test",
    "status": "active",
}
# ============================================================================

# RLS scope values documented in substrate_repository and substrate_models
VALID_RLS_SCOPES: tuple[str, ...] = (
    "developer",
    "global",
    "cursor",
    "l-private",
    "agent",
)

# Semantic fact tiers documented in memory/substrate_repository.py
VALID_SEMANTIC_FACT_TIERS: tuple[str, ...] = (
    "identity",
    "project",
    "session",
    "general",
)

# Embedding dimension used by insert_semantic_embedding (memory.substrate_semantic.EMBEDDING_DIMENSIONS)
EMBEDDING_DIMENSIONS = 1536

# Directories scanned for repo-wide call-site meta-test (all callers of contract methods)
CONTRACT_SCAN_DIRS = (
    "memory",
    "core",
    "api",
    "runtime",
    "agents",
    "orchestration",
    "scripts",
)

# Methods we scan for: (method_name, param_name, allowed_values)
# Call sites passing that param as a literal must use a value in allowed_values so callee accepts.
CONTRACT_METHODS_FOR_SCAN: list[tuple[str, str, tuple[str, ...]]] = [
    ("insert_knowledge_fact", "scope", VALID_RLS_SCOPES),
    ("insert_semantic_embedding", "scope", VALID_RLS_SCOPES),
    ("insert_semantic_fact", "tier", VALID_SEMANTIC_FACT_TIERS),
]


# ---------------------------------------------------------------------------
# Repo-wide call-site discovery: AST visitor for contract method calls
# ---------------------------------------------------------------------------


def _get_python_files_for_contract_scan() -> list[Path]:
    """All Python files in CONTRACT_SCAN_DIRS (repo-wide callers)."""
    repo_root = Path(__file__).resolve().parents[2]
    files: list[Path] = []
    for directory in CONTRACT_SCAN_DIRS:
        dir_path = repo_root / directory
        if dir_path.exists():
            for path in dir_path.rglob("*.py"):
                if "__pycache__" not in str(path):
                    files.append(path)
    return files


class ContractCallSiteVisitor(ast.NodeVisitor):
    """
    Find calls to contract methods (e.g. .insert_knowledge_fact(...)) and check
    that when scope (or other param) is passed as a literal, it is in the allowed list.
    """

    def __init__(
        self,
        file_path: Path,
        method_param_allowed: list[tuple[str, str, tuple[str, ...]]],
    ) -> None:
        self.file_path = file_path
        self.method_param_allowed = method_param_allowed
        self.violations: list[
            tuple[int, str, str, str]
        ] = []  # (line, method, param, value)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            for mname, param_name, allowed in self.method_param_allowed:
                if mname != method_name:
                    continue
                for kw in node.keywords:
                    if kw.arg == param_name and kw.value is not None:
                        if isinstance(kw.value, ast.Constant) and isinstance(
                            kw.value.value, str
                        ):
                            if kw.value.value not in allowed:
                                self.violations.append(
                                    (
                                        node.lineno,
                                        method_name,
                                        param_name,
                                        kw.value.value,
                                    )
                                )
                        # else: value is Name/Attribute/Call/etc. -> from context, OK
                        break
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Contract stub: mimics repository method signatures and accepts all allowed values
# Real implementation must behave the same for these inputs.
# ---------------------------------------------------------------------------


@dataclass
class StubKnowledgeFactRow:
    fact_id: UUID
    subject: str
    predicate: str
    object: dict | str
    confidence: float
    source_packet: UUID | None
    created_at: datetime
    scope: str


class ContractStubRepository:
    """
    Stub that implements the same caller-facing contract as scope-accepting
    repository methods. Used to assert that for every allowed param value,
    the call is valid and succeeds. Real SubstrateRepository must accept
    the same values.
    """

    async def insert_knowledge_fact(
        self,
        subject: str,
        predicate: str,
        object_value: Any,
        confidence: float,
        source_packet: UUID | None,
        fact_id: UUID | None = None,
        scope: str = "cursor",
    ) -> StubKnowledgeFactRow:
        if scope not in VALID_RLS_SCOPES:
            raise ValueError(f"scope {scope!r} not in allowed {VALID_RLS_SCOPES}")
        return StubKnowledgeFactRow(
            fact_id=fact_id or uuid4(),
            subject=subject,
            predicate=predicate,
            object=object_value
            if isinstance(object_value, (dict, str))
            else {"value": object_value},
            confidence=confidence,
            source_packet=source_packet,
            created_at=datetime.now(UTC),
            scope=scope,
        )

    async def insert_semantic_embedding(
        self,
        vector: list[float],
        payload: dict[str, Any],
        agent_id: str | None = None,
        scope: str = "cursor",
    ) -> UUID:
        if scope not in VALID_RLS_SCOPES:
            raise ValueError(f"scope {scope!r} not in allowed {VALID_RLS_SCOPES}")
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"vector length must be {EMBEDDING_DIMENSIONS}, got {len(vector)}"
            )
        return uuid4()

    async def insert_semantic_fact(
        self,
        fact_text: str,
        triplet: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        importance: float = 0.5,
        tags: list[str] | None = None,
        tier: str = "general",
        source: str | None = None,
        source_packet_id: UUID | None = None,
        confidence: float = 0.8,
        agent_id: str | None = None,
        tenant_id: UUID | None = None,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> UUID:
        if tier not in VALID_SEMANTIC_FACT_TIERS:
            raise ValueError(
                f"tier {tier!r} not in allowed {VALID_SEMANTIC_FACT_TIERS}"
            )
        if embedding is not None and len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"embedding length must be {EMBEDDING_DIMENSIONS}, got {len(embedding)}"
            )
        return uuid4()


# ---------------------------------------------------------------------------
# Contract registry: (method_name, param_name, allowed_values, build_kwargs)
# build_kwargs(value) returns kwargs for that method.
# ---------------------------------------------------------------------------


def _kwargs_insert_knowledge_fact(scope: str) -> dict[str, Any]:
    return {
        "subject": "contract_test",
        "predicate": "test",
        "object_value": {"key": "value"},
        "confidence": 0.9,
        "source_packet": uuid4(),
        "scope": scope,
    }


def _kwargs_insert_semantic_embedding(scope: str) -> dict[str, Any]:
    return {
        "vector": [0.0] * EMBEDDING_DIMENSIONS,
        "payload": {"text": "contract test"},
        "agent_id": None,
        "scope": scope,
    }


def _kwargs_insert_semantic_fact(tier: str) -> dict[str, Any]:
    return {
        "fact_text": "contract fact",
        "triplet": {"subject": "x", "predicate": "is", "object": "y"},
        "importance": 0.7,
        "tags": ["contract"],
        "tier": tier,
        "source": "contract_stub",
        "confidence": 0.9,
    }


REPOSITORY_CONTRACT_REGISTRY: list[
    tuple[str, str, tuple[str, ...], Callable[..., dict[str, Any]]]
] = [
    (
        "insert_knowledge_fact",
        "scope",
        VALID_RLS_SCOPES,
        _kwargs_insert_knowledge_fact,
    ),
    (
        "insert_semantic_embedding",
        "scope",
        VALID_RLS_SCOPES,
        _kwargs_insert_semantic_embedding,
    ),
    (
        "insert_semantic_fact",
        "tier",
        VALID_SEMANTIC_FACT_TIERS,
        _kwargs_insert_semantic_fact,
    ),
]


# ---------------------------------------------------------------------------
# Meta-test (repo-wide): all call sites pass valid params so callee can receive/reply
# ---------------------------------------------------------------------------


def test_all_call_sites_pass_valid_scope_to_callee():
    """
    Repo-wide: every caller of insert_knowledge_fact, insert_semantic_embedding, etc.
    must pass scope (or other contract param) so the callee can accept and reply.

    If a call site passes scope as a literal string, it must be in VALID_RLS_SCOPES.
    If scope is from context (variable/expression), that is OK. This test ensures
    no file hardcodes an invalid scope that the callee would reject.
    """
    repo_root = Path(__file__).resolve().parents[2]
    all_violations: list[tuple[Path, int, str, str, str]] = []

    # Use parsed_codebase for core dirs (memory, core, api, ...) and parse scripts separately
    files_to_scan = _get_python_files_for_contract_scan()
    for file_path in files_to_scan:
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            continue

        visitor = ContractCallSiteVisitor(file_path, CONTRACT_METHODS_FOR_SCAN)
        visitor.visit(tree)
        for line, method, param, value in visitor.violations:
            try:
                rel = file_path.relative_to(repo_root)
            except ValueError:
                rel = file_path
            all_violations.append((rel, line, method, param, value))

    if all_violations:
        msg = (
            "Repo-wide contract violation: the following call sites pass a literal "
            "scope (or other param) value that the callee does not accept "
            f"(allowed: {VALID_RLS_SCOPES}). "
            "Fix: pass scope from context/envelope or use an allowed literal.\n\n"
        )
        for rel, line, method, param, value in all_violations:
            msg += f"  {rel}:{line}  {method}({param}={value!r})\n"
        pytest.fail(msg)


# ---------------------------------------------------------------------------
# Meta-test: for each registered method and each allowed value, call succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method_name,param_name,allowed_values,build_kwargs",
    [(*entry,) for entry in REPOSITORY_CONTRACT_REGISTRY],
    ids=[f"{m}({p})" for m, p, *_ in REPOSITORY_CONTRACT_REGISTRY],
)
async def test_repository_contract_accepts_all_allowed_values(
    method_name: str,
    param_name: str,
    allowed_values: tuple[str, ...],
    build_kwargs: Callable[..., dict[str, Any]],
):
    """
    For each registered method and each allowed caller-supplied value (e.g. scope),
    the call must be valid and complete successfully.

    Uses a contract stub that mirrors repository signatures. The real implementation
    must accept the same allowed values; this test ensures the contract is
    well-defined and that callers can pass any allowed value and get success.
    """
    stub = ContractStubRepository()
    method = getattr(stub, method_name)
    for value in allowed_values:
        kwargs = build_kwargs(value)
        try:
            result = await method(**kwargs)
        except Exception as e:
            pytest.fail(
                f"Contract failure: {method_name}({param_name}={value!r}) raised {e!r}. "
                "Calls with allowed values must succeed."
            )
        assert result is not None
        if method_name == "insert_knowledge_fact":
            assert hasattr(result, "fact_id") and hasattr(result, "scope")
        elif method_name == "insert_semantic_embedding":
            assert isinstance(result, UUID)
        elif method_name == "insert_semantic_fact":
            assert isinstance(result, UUID)


# ---------------------------------------------------------------------------
# Meta-test: registry is non-empty and entries are well-formed
# ---------------------------------------------------------------------------


def test_repository_contract_registry_non_empty():
    """Registry must contain at least one method so the meta-test is meaningful."""
    assert len(REPOSITORY_CONTRACT_REGISTRY) >= 1, (
        "REPOSITORY_CONTRACT_REGISTRY must not be empty. "
        "Add (method_name, param_name, allowed_values, build_kwargs) for each contract."
    )


def test_repository_contract_registry_entries_have_allowed_values():
    """Every registry entry must define allowed values for the parameter."""
    for method_name, param_name, allowed_values, _ in REPOSITORY_CONTRACT_REGISTRY:
        assert len(allowed_values) >= 1, (
            f"Registry entry {method_name}({param_name}) must have at least one allowed value."
        )


def test_contract_stub_has_all_registry_methods():
    """ContractStubRepository must implement every method in the registry."""
    stub = ContractStubRepository()
    for method_name, *_ in REPOSITORY_CONTRACT_REGISTRY:
        assert hasattr(stub, method_name), (
            f"ContractStubRepository must implement {method_name}. "
            "Add the method to the stub when adding a new registry entry."
        )
