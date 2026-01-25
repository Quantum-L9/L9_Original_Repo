"""
L9 Core Governance - Policy Generator
======================================

Utility to generate YAML governance policies from templates.

Features:
- Template presets (allow, deny, scope-access, tool-approval)
- Auto-generates DORA metadata
- Validates required fields
- CLI and programmatic interfaces

Usage:
    # Programmatic
    from core.governance.policy_generator import PolicyGenerator
    
    gen = PolicyGenerator()
    yaml_str = gen.generate_allow_policy(
        id="allow-memory-read",
        name="Allow Memory Read",
        subjects=["L", "C"],
        actions=["memory.read"],
        resources=["scope:developer"],
        priority=100,
    )
    
    # CLI
    python -m core.governance.policy_generator --template allow \\
        --id "allow-test" --name "Test Policy" --subjects L,C \\
        --actions "test.*" --resources "*" --output config/policies/test.yaml

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Policy Generator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T12:00:00Z",
    "updated_at": "2026-01-20T12:00:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "policy_generator",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import structlog
import yaml

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class PolicySpec:
    """Specification for a single policy."""

    id: str
    name: str
    effect: str  # "allow" or "deny"
    subjects: List[str]
    actions: List[str]
    resources: List[str]
    priority: int = 100
    description: str = ""
    enabled: bool = True
    conditions: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate policy spec."""
        if self.effect not in ("allow", "deny"):
            raise ValueError(f"effect must be 'allow' or 'deny', got '{self.effect}'")
        if not self.id:
            raise ValueError("id is required")
        if not self.name:
            raise ValueError("name is required")
        if not self.subjects:
            raise ValueError("subjects cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description
            or f"{self.effect.title()} policy: {self.name}",
            "effect": self.effect,
            "priority": self.priority,
            "subjects": self.subjects,
            "actions": self.actions if self.actions else [],
            "resources": self.resources,
            "enabled": self.enabled,
        }
        if self.conditions:
            result["conditions"] = self.conditions
        return result


@dataclass
class ScopeAccessSpec:
    """Specification for scope access matrix entry."""

    caller_id: str
    allowed_scopes: List[str]
    denied_scopes: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "allowed_scopes": self.allowed_scopes,
            "description": self.description or f"Access rules for {self.caller_id}",
        }
        if self.denied_scopes:
            result["denied_scopes"] = self.denied_scopes
        return result


@dataclass
class PolicyFileSpec:
    """Specification for a complete policy file."""

    file_name: str
    component_name: str
    description: str = ""
    policies: List[PolicySpec] = field(default_factory=list)
    scope_access_matrix: Dict[str, ScopeAccessSpec] = field(default_factory=dict)
    extra_sections: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Policy Generator
# =============================================================================


class PolicyGenerator:
    """
    Generates YAML governance policies from templates.

    Supports:
    - Simple allow/deny policies
    - Scope access matrices
    - Tool approval policies
    - Custom policy structures
    """

    def __init__(self, author: str = "Igor Beylin"):
        """
        Initialize generator.

        Args:
            author: Author name for DORA metadata
        """
        self.author = author

    # -------------------------------------------------------------------------
    # DORA Metadata
    # -------------------------------------------------------------------------

    def _generate_dora_header(
        self,
        component_name: str,
        file_name: str,
        policy_type: str = "policy",
    ) -> str:
        """Generate DORA metadata header."""
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"""# ============================================================================
# DORA META - AUTO-GENERATED
# ============================================================================
# component_name: "{component_name}"
# module_version: "1.0.0"
# created_by: "{self.author}"
# created_at: "{now}"
# updated_at: "{now}"
# layer: "foundation"
# domain: "configuration"
# file_name: "{file_name}"
# type: "{policy_type}"
# status: "active"
# ============================================================================
"""

    def _generate_dora_footer(self, tags: List[str], keywords: List[str]) -> str:
        """Generate DORA metadata footer."""
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        tags_str = ", ".join(f'"{t}"' for t in tags)
        keywords_str = ", ".join(f'"{k}"' for k in keywords)
        return f"""
# ============================================================================
# DORA FOOTER - AUTO-GENERATED
# ============================================================================
# tags: [{tags_str}]
# keywords: [{keywords_str}]
# last_modified: "{now}"
# ============================================================================
"""

    # -------------------------------------------------------------------------
    # Simple Policy Templates
    # -------------------------------------------------------------------------

    def generate_allow_policy(
        self,
        id: str,
        name: str,
        subjects: List[str],
        actions: List[str],
        resources: List[str],
        priority: int = 100,
        description: str = "",
        conditions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a single allow policy dict.

        Args:
            id: Unique policy identifier
            name: Human-readable name
            subjects: List of subjects (e.g., ["L", "C", "agent:*"])
            actions: List of actions (e.g., ["memory.read", "memory.write"])
            resources: List of resources (e.g., ["scope:developer"])
            priority: Policy priority (higher = evaluated first)
            description: Policy description
            conditions: Optional conditions dict

        Returns:
            Policy dictionary ready for YAML serialization
        """
        spec = PolicySpec(
            id=id,
            name=name,
            effect="allow",
            subjects=subjects,
            actions=actions,
            resources=resources,
            priority=priority,
            description=description,
            conditions=conditions,
        )
        return spec.to_dict()

    def generate_deny_policy(
        self,
        id: str,
        name: str,
        subjects: List[str],
        actions: List[str],
        resources: List[str],
        priority: int = 100,
        description: str = "",
        conditions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a single deny policy dict."""
        spec = PolicySpec(
            id=id,
            name=name,
            effect="deny",
            subjects=subjects,
            actions=actions,
            resources=resources,
            priority=priority,
            description=description,
            conditions=conditions,
        )
        return spec.to_dict()

    # -------------------------------------------------------------------------
    # Complete Policy File Generation
    # -------------------------------------------------------------------------

    def generate_policy_file(
        self,
        file_name: str,
        component_name: str,
        policies: List[Dict[str, Any]],
        description: str = "",
        scope_access_matrix: Optional[Dict[str, Dict[str, Any]]] = None,
        extra_sections: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a complete policy YAML file.

        Args:
            file_name: Name of the file (without extension)
            component_name: Human-readable component name
            policies: List of policy dicts
            description: File description comment
            scope_access_matrix: Optional scope access matrix
            extra_sections: Optional additional YAML sections

        Returns:
            Complete YAML string with DORA metadata
        """
        # Build YAML content
        content_dict: Dict[str, Any] = {}

        if scope_access_matrix:
            content_dict["scope_access_matrix"] = scope_access_matrix

        if policies:
            content_dict["policies"] = policies

        if extra_sections:
            content_dict.update(extra_sections)

        # Generate YAML
        yaml_content = yaml.dump(
            content_dict,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )

        # Build description comment
        desc_comment = ""
        if description:
            desc_lines = description.strip().split("\n")
            desc_comment = "\n".join(f"# {line}" for line in desc_lines) + "\n\n"

        # Extract keywords from policies
        keywords = set()
        for p in policies:
            keywords.add(p.get("id", "").split("-")[0])
            keywords.update(p.get("actions", [])[:2])
        keywords = list(keywords)[:5]

        # Assemble file
        result = (
            self._generate_dora_header(component_name, file_name)
            + "\n"
            + desc_comment
            + yaml_content
            + self._generate_dora_footer(
                tags=["configuration", "foundation", "policy"],
                keywords=keywords or ["policy"],
            )
        )

        return result

    # -------------------------------------------------------------------------
    # Template Presets
    # -------------------------------------------------------------------------

    def from_template(
        self,
        template: str,
        file_name: str,
        **kwargs: Any,
    ) -> str:
        """
        Generate policy file from a named template.

        Templates:
        - "scope-access": Memory scope access matrix
        - "tool-approval": Tool approval policies
        - "resource-access": Generic resource access policies

        Args:
            template: Template name
            file_name: Output file name
            **kwargs: Template-specific parameters

        Returns:
            Complete YAML string
        """
        if template == "scope-access":
            return self._template_scope_access(file_name, **kwargs)
        elif template == "tool-approval":
            return self._template_tool_approval(file_name, **kwargs)
        elif template == "resource-access":
            return self._template_resource_access(file_name, **kwargs)
        else:
            raise ValueError(f"Unknown template: {template}")

    def _template_scope_access(
        self,
        file_name: str,
        scopes: List[str],
        callers: Dict[str, List[str]],
        default_caller: str = "default",
    ) -> str:
        """
        Generate scope access policy file.

        Args:
            file_name: Output file name
            scopes: List of available scopes
            callers: Dict mapping caller_id -> allowed_scopes
            default_caller: Caller ID for default access rules
        """
        # Build scope access matrix
        scope_matrix = {}
        for caller_id, allowed in callers.items():
            denied = [s for s in scopes if s not in allowed]
            scope_matrix[caller_id] = {
                "allowed_scopes": allowed,
                "description": f"Access rules for {caller_id}",
            }
            if denied:
                scope_matrix[caller_id]["denied_scopes"] = denied

        # Build policies
        policies = []
        for scope in scopes:
            # Find callers that have access to this scope
            allowed_subjects = [c for c, s in callers.items() if scope in s]
            if allowed_subjects:
                policies.append(
                    self.generate_allow_policy(
                        id=f"allow-{scope}-scope",
                        name=f"Allow {scope.title()} Scope Access",
                        subjects=(
                            allowed_subjects + ["*"]
                            if "*" in allowed_subjects
                            else allowed_subjects
                        ),
                        actions=["memory.read", "memory.write", "memory.delete"],
                        resources=[f"scope:{scope}"],
                        priority=100,
                        description=f"Permits access to {scope}-scoped memories.",
                    )
                )

        return self.generate_policy_file(
            file_name=file_name,
            component_name=f"{file_name.replace('_', ' ').title()} Policies",
            policies=policies,
            description=f"Scope access policies for {', '.join(scopes)}",
            scope_access_matrix=scope_matrix,
        )

    def _template_tool_approval(
        self,
        file_name: str,
        high_risk_tools: List[str],
        auto_approve_tools: List[str],
        approvers: List[str] = None,
    ) -> str:
        """
        Generate tool approval policy file.

        Args:
            file_name: Output file name
            high_risk_tools: Tools requiring Igor approval
            auto_approve_tools: Tools that are auto-approved
            approvers: List of approvers (default: ["Igor"])
        """
        approvers = approvers or ["Igor"]

        policies = []

        # Auto-approve policies
        if auto_approve_tools:
            policies.append(
                self.generate_allow_policy(
                    id="auto-approve-safe-tools",
                    name="Auto-Approve Safe Tools",
                    subjects=["L", "C", "agent:*"],
                    actions=[f"tool.execute.{t}" for t in auto_approve_tools],
                    resources=["*"],
                    priority=200,
                    description="Low-risk tools that are automatically approved.",
                )
            )

        # High-risk tool policies (require approval)
        if high_risk_tools:
            policies.append(
                self.generate_deny_policy(
                    id="require-approval-high-risk",
                    name="Require Approval for High-Risk Tools",
                    subjects=["*"],
                    actions=[f"tool.execute.{t}" for t in high_risk_tools],
                    resources=["*"],
                    priority=150,
                    description=f"High-risk tools require approval from: {', '.join(approvers)}",
                    conditions={
                        "requires_approval": True,
                        "approvers": approvers,
                    },
                )
            )

        return self.generate_policy_file(
            file_name=file_name,
            component_name="Tool Approval Policies",
            policies=policies,
            description=f"Tool approval policies.\nHigh-risk: {', '.join(high_risk_tools)}\nAuto-approve: {', '.join(auto_approve_tools)}",
        )

    def _template_resource_access(
        self,
        file_name: str,
        resource_type: str,
        read_subjects: List[str],
        write_subjects: List[str],
        admin_subjects: List[str] = None,
    ) -> str:
        """
        Generate resource access policy file.

        Args:
            file_name: Output file name
            resource_type: Resource type (e.g., "config", "kernel", "memory")
            read_subjects: Subjects with read access
            write_subjects: Subjects with write access
            admin_subjects: Subjects with admin access (optional)
        """
        policies = []

        # Read access
        policies.append(
            self.generate_allow_policy(
                id=f"allow-{resource_type}-read",
                name=f"Allow {resource_type.title()} Read",
                subjects=read_subjects,
                actions=[f"{resource_type}.read", f"{resource_type}.list"],
                resources=[f"{resource_type}:*"],
                priority=100,
            )
        )

        # Write access
        policies.append(
            self.generate_allow_policy(
                id=f"allow-{resource_type}-write",
                name=f"Allow {resource_type.title()} Write",
                subjects=write_subjects,
                actions=[f"{resource_type}.write", f"{resource_type}.update"],
                resources=[f"{resource_type}:*"],
                priority=100,
            )
        )

        # Admin access
        if admin_subjects:
            policies.append(
                self.generate_allow_policy(
                    id=f"allow-{resource_type}-admin",
                    name=f"Allow {resource_type.title()} Admin",
                    subjects=admin_subjects,
                    actions=[f"{resource_type}.*"],
                    resources=[f"{resource_type}:*"],
                    priority=200,
                )
            )

        # Default deny
        policies.append(
            self.generate_deny_policy(
                id=f"deny-{resource_type}-default",
                name=f"Deny {resource_type.title()} by Default",
                subjects=["*"],
                actions=[f"{resource_type}.*"],
                resources=[f"{resource_type}:*"],
                priority=0,
                description="Default deny for unauthorized access.",
            )
        )

        return self.generate_policy_file(
            file_name=file_name,
            component_name=f"{resource_type.title()} Access Policies",
            policies=policies,
            description=f"Access control policies for {resource_type} resources.",
        )

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------

    def write_policy_file(
        self,
        content: str,
        output_path: Union[str, Path],
        overwrite: bool = False,
    ) -> Path:
        """
        Write policy content to file.

        Args:
            content: YAML content string
            output_path: Output file path
            overwrite: Whether to overwrite existing file

        Returns:
            Path to written file
        """
        path = Path(output_path)

        if path.exists() and not overwrite:
            raise FileExistsError(
                f"File exists: {path}. Use overwrite=True to replace."
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        logger.info(f"Policy file written: {path}")
        return path


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate YAML governance policies from templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate scope access policies
  python -m core.governance.policy_generator --template scope-access \\
      --file-name my_scope_policy \\
      --scopes developer,global,private \\
      --callers "L:developer,global,private" "C:developer,global"

  # Generate tool approval policies
  python -m core.governance.policy_generator --template tool-approval \\
      --file-name tool_approval \\
      --high-risk gmprun,gitcommit,macagent \\
      --auto-approve search,read,list

  # Generate resource access policies
  python -m core.governance.policy_generator --template resource-access \\
      --file-name config_access \\
      --resource-type config \\
      --read-subjects L,C,agent \\
      --write-subjects L \\
      --admin-subjects Igor
        """,
    )

    parser.add_argument(
        "--template",
        choices=["scope-access", "tool-approval", "resource-access"],
        required=True,
        help="Policy template to use",
    )
    parser.add_argument(
        "--file-name", required=True, help="Output file name (without .yaml)"
    )
    parser.add_argument("--output", help="Output directory (default: config/policies/)")
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing file"
    )

    # Scope access template args
    parser.add_argument("--scopes", help="Comma-separated list of scopes")
    parser.add_argument(
        "--callers",
        nargs="+",
        help="Caller access rules (format: caller:scope1,scope2)",
    )

    # Tool approval template args
    parser.add_argument("--high-risk", help="Comma-separated high-risk tools")
    parser.add_argument("--auto-approve", help="Comma-separated auto-approve tools")

    # Resource access template args
    parser.add_argument("--resource-type", help="Resource type name")
    parser.add_argument("--read-subjects", help="Comma-separated read subjects")
    parser.add_argument("--write-subjects", help="Comma-separated write subjects")
    parser.add_argument("--admin-subjects", help="Comma-separated admin subjects")

    args = parser.parse_args()

    gen = PolicyGenerator()

    # Parse template-specific args and generate
    if args.template == "scope-access":
        if not args.scopes or not args.callers:
            parser.error("--scopes and --callers required for scope-access template")

        scopes = [s.strip() for s in args.scopes.split(",")]
        callers = {}
        for c in args.callers:
            caller_id, scope_list = c.split(":")
            callers[caller_id] = [s.strip() for s in scope_list.split(",")]

        content = gen.from_template(
            "scope-access", args.file_name, scopes=scopes, callers=callers
        )

    elif args.template == "tool-approval":
        high_risk = [t.strip() for t in (args.high_risk or "").split(",") if t.strip()]
        auto_approve = [
            t.strip() for t in (args.auto_approve or "").split(",") if t.strip()
        ]

        content = gen.from_template(
            "tool-approval",
            args.file_name,
            high_risk_tools=high_risk,
            auto_approve_tools=auto_approve,
        )

    elif args.template == "resource-access":
        if not args.resource_type:
            parser.error("--resource-type required for resource-access template")

        read_subjects = [
            s.strip() for s in (args.read_subjects or "").split(",") if s.strip()
        ]
        write_subjects = [
            s.strip() for s in (args.write_subjects or "").split(",") if s.strip()
        ]
        admin_subjects = [
            s.strip() for s in (args.admin_subjects or "").split(",") if s.strip()
        ] or None

        content = gen.from_template(
            "resource-access",
            args.file_name,
            resource_type=args.resource_type,
            read_subjects=read_subjects,
            write_subjects=write_subjects,
            admin_subjects=admin_subjects,
        )

    # Output
    output_dir = Path(args.output) if args.output else Path("config/policies")
    output_path = output_dir / f"{args.file_name}.yaml"

    gen.write_policy_file(content, output_path, overwrite=args.overwrite)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-GOV-001",
    "governance_level": "standard",
    "compliance_required": True,
    "audit_trail": False,
    "dependencies": [],
    "tags": ["governance", "foundation", "utility", "generator"],
    "keywords": ["policy", "yaml", "generator", "template"],
    "business_value": "Generates governance policies from templates",
    "last_modified": "2026-01-20T12:00:00Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial implementation",
}
# ============================================================================
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
