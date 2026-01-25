"""
Session DAG Registry
====================

Global registry for session DAGs with auto-discovery.

Version: 1.0.0
"""

from __future__ import annotations

from typing import Any

import structlog

from orchestrators.session.interface import SessionDAG

logger = structlog.get_logger(__name__)


class SessionDAGRegistry:
    """
    Registry for Session DAGs.

    Provides:
    - Registration of DAGs
    - Lookup by ID or name
    - Listing all available DAGs
    - Validation on registration
    """

    def __init__(self):
        self._dags: dict[str, SessionDAG] = {}
        self._by_name: dict[str, str] = {}  # name -> id mapping

    def register(self, dag: SessionDAG) -> None:
        """
        Register a session DAG.

        Args:
            dag: SessionDAG to register

        Raises:
            ValueError: If DAG validation fails or ID already registered
        """
        # Validate DAG structure
        errors = dag.validate()
        if errors:
            raise ValueError(f"DAG validation failed: {errors}")

        # Check for duplicate ID
        if dag.id in self._dags:
            raise ValueError(f"DAG with ID '{dag.id}' already registered")

        # Register
        self._dags[dag.id] = dag
        self._by_name[dag.name.lower()] = dag.id

        logger.info(
            f"Session DAG registered: {dag.name}",
            dag_id=dag.id,
            version=dag.version,
            nodes=len(dag.nodes),
        )

    def get(self, dag_id: str) -> SessionDAG | None:
        """Get DAG by ID."""
        return self._dags.get(dag_id)

    def get_by_name(self, name: str) -> SessionDAG | None:
        """Get DAG by name (case-insensitive)."""
        dag_id = self._by_name.get(name.lower())
        return self._dags.get(dag_id) if dag_id else None

    def list_all(self) -> list[dict[str, Any]]:
        """List all registered DAGs."""
        return [
            {
                "id": dag.id,
                "name": dag.name,
                "version": dag.version,
                "description": dag.description[:100] + "..." if len(dag.description) > 100 else dag.description,
                "nodes": len(dag.nodes),
                "tags": dag.tags,
            }
            for dag in self._dags.values()
        ]

    def __len__(self) -> int:
        return len(self._dags)

    def __contains__(self, dag_id: str) -> bool:
        return dag_id in self._dags


# Global registry singleton
session_dag_registry = SessionDAGRegistry()


def register_session_dag(dag: SessionDAG) -> None:
    """Register a session DAG in the global registry."""
    session_dag_registry.register(dag)


def get_session_dag(dag_id: str) -> SessionDAG | None:
    """Get a session DAG by ID or name."""
    dag = session_dag_registry.get(dag_id)
    if dag is None:
        dag = session_dag_registry.get_by_name(dag_id)
    return dag


def list_session_dags() -> list[dict[str, Any]]:
    """List all registered session DAGs."""
    return session_dag_registry.list_all()
