#!/usr/bin/env python3
"""
L9 Dead Code Audit - Phase 3: Risk Categorization
==================================================

Classifies findings by risk level and determines fix strategy:
- HIGH: Config fields (likely bugs), public methods
- MEDIUM: Private methods, internal constants
- LOW: Unused imports, test fixtures

Actions:
- WIRE_UP: Config field should be connected to functionality
- DELETE: Truly dead code, safe to remove
- NOQA: Intentional, add comment
- REVIEW: Needs manual review

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Phase 3: Risk Categorization",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "categorize_dead_code",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import json
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent

# =============================================================================
# ENUMS
# =============================================================================

class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FixAction(str, Enum):
    WIRE_UP = "WIRE_UP"      # Connect config field to functionality
    DELETE = "DELETE"        # Remove dead code
    NOQA = "NOQA"           # Add noqa comment (intentional)
    REVIEW = "REVIEW"        # Needs manual review
    AUTO_FIX = "AUTO_FIX"   # Can be auto-fixed by ruff


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class CategorizedFinding:
    """A finding with risk categorization."""
    file: str
    line: int
    symbol: str
    symbol_type: str
    confidence: float
    source: str
    message: str
    context: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    action: FixAction = FixAction.REVIEW
    action_reason: str = ""
    auto_fixable: bool = False
    test_needed: bool = False
    proposed_fix: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        d["action"] = self.action.value
        return d


@dataclass
class CategorizationResult:
    """Result of risk categorization."""
    total_findings: int
    high_risk: list[CategorizedFinding] = field(default_factory=list)
    medium_risk: list[CategorizedFinding] = field(default_factory=list)
    low_risk: list[CategorizedFinding] = field(default_factory=list)
    auto_fixable_count: int = 0
    manual_review_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_findings": self.total_findings,
            "summary": {
                "high_risk": len(self.high_risk),
                "medium_risk": len(self.medium_risk),
                "low_risk": len(self.low_risk),
                "auto_fixable": self.auto_fixable_count,
                "manual_review": self.manual_review_count,
            },
            "high_risk": [f.to_dict() for f in self.high_risk],
            "medium_risk": [f.to_dict() for f in self.medium_risk],
            "low_risk": [f.to_dict() for f in self.low_risk],
        }


# =============================================================================
# CATEGORIZATION RULES
# =============================================================================

# Confidence thresholds by symbol type
CONFIDENCE_THRESHOLDS = {
    "dataclass_field": 0.95,     # Almost certainly a bug if unused
    "import": 0.98,             # Very safe to remove
    "variable": 0.95,           # Usually safe
    "argument": 0.90,           # May be for API compatibility
    "function": 0.85,           # Could be called dynamically
    "method": 0.80,             # Could be overridden/called dynamically
    "class": 0.75,              # Could be used in type hints
    "class_attribute": 0.80,    # Could be accessed dynamically
    "dead_branch": 0.98,        # Very safe to remove
}

# Risk levels by symbol type
RISK_BY_TYPE = {
    "dataclass_field": RiskLevel.HIGH,
    "class_attribute": RiskLevel.MEDIUM,
    "method": RiskLevel.MEDIUM,
    "function": RiskLevel.MEDIUM,
    "class": RiskLevel.MEDIUM,
    "import": RiskLevel.LOW,
    "variable": RiskLevel.LOW,
    "argument": RiskLevel.LOW,
    "dead_branch": RiskLevel.LOW,
}

# Actions by symbol type
ACTION_BY_TYPE = {
    "dataclass_field": FixAction.WIRE_UP,
    "import": FixAction.AUTO_FIX,
    "variable": FixAction.DELETE,
    "argument": FixAction.REVIEW,
    "function": FixAction.DELETE,
    "method": FixAction.DELETE,
    "class": FixAction.REVIEW,
    "class_attribute": FixAction.DELETE,
    "dead_branch": FixAction.AUTO_FIX,
}


def categorize_finding(finding: dict[str, Any]) -> CategorizedFinding:
    """Categorize a single finding by risk and action."""
    symbol_type = finding.get("symbol_type", "unknown")
    confidence = finding.get("confidence", 0.5)
    file_path = finding.get("file", "")
    symbol = finding.get("symbol", "")
    
    # Determine risk level
    risk_level = RISK_BY_TYPE.get(symbol_type, RiskLevel.MEDIUM)
    
    # Adjust risk based on file location
    if "/core/" in file_path or "/memory/" in file_path:
        # Core modules are higher risk
        if risk_level == RiskLevel.LOW:
            risk_level = RiskLevel.MEDIUM
    elif "/tests/" in file_path:
        # Test files are lower risk
        risk_level = RiskLevel.LOW
    
    # Determine action
    action = ACTION_BY_TYPE.get(symbol_type, FixAction.REVIEW)
    action_reason = ""
    auto_fixable = False
    test_needed = False
    proposed_fix = ""
    
    # Refine action based on specifics
    if symbol_type == "dataclass_field":
        # Extract class name and field name
        class_name = symbol.split(".")[0] if "." in symbol else ""
        field_name = symbol.split(".")[-1] if "." in symbol else symbol
        
        # Check if this is a Result/Response/Output class (serialized, not directly accessed)
        result_class_patterns = ["Result", "Response", "Output", "Info", "Data", "State", "Context", "Snapshot"]
        is_result_class = any(p in class_name for p in result_class_patterns)
        
        # Check if field is observability-related (metrics, timestamps)
        observability_patterns = ["_ms", "_count", "_at", "_time", "_duration", "_bytes", "_size", "_timestamp"]
        is_observability_field = any(field_name.endswith(p) for p in observability_patterns)
        
        # Check if this is a Config class (should be wired up)
        config_class_patterns = ["Config", "Settings", "Options", "Params"]
        is_config_class = any(p in class_name for p in config_class_patterns)
        
        if is_config_class:
            # Config fields that aren't used are likely bugs
            action = FixAction.WIRE_UP
            action_reason = "Config field defined but never used—likely bug or needs wiring"
            test_needed = True
            proposed_fix = f"Wire '{symbol}' to functionality or delete if unnecessary"
            risk_level = RiskLevel.HIGH
        elif is_result_class or is_observability_field:
            # Result/Response fields are typically serialized, not directly accessed
            action = FixAction.NOQA
            action_reason = "Result/Response field used in serialization (JSON output)"
            proposed_fix = f"Field '{field_name}' is likely serialized—add to .vultureignore"
            risk_level = RiskLevel.LOW
        else:
            # Unknown dataclass - default to REVIEW
            action = FixAction.REVIEW
            action_reason = "Dataclass field may be unused or accessed indirectly"
            proposed_fix = f"Review if '{symbol}' is used via serialization or can be deleted"
            risk_level = RiskLevel.MEDIUM
        
    elif symbol_type == "import":
        action = FixAction.AUTO_FIX
        action_reason = "Unused import can be auto-removed by ruff"
        auto_fixable = True
        proposed_fix = f"Run: ruff check --fix {file_path}"
        
    elif symbol_type == "variable":
        action = FixAction.DELETE
        action_reason = "Local variable assigned but never used"
        auto_fixable = False  # Need manual review
        proposed_fix = "Remove variable assignment or use the variable"
        
    elif symbol_type == "argument":
        action = FixAction.REVIEW
        action_reason = "Unused argument—may be for API compatibility"
        proposed_fix = "Remove if not needed for API, or prefix with _ to indicate intentional"
        
    elif symbol_type == "method":
        if symbol.startswith("_"):
            action = FixAction.DELETE
            action_reason = "Private method never called internally"
            proposed_fix = "Delete method or add # noqa: vulture if intentional"
        else:
            action = FixAction.REVIEW
            action_reason = "Public method may be part of API"
            risk_level = RiskLevel.HIGH
            test_needed = True
            proposed_fix = "Review if part of public API before deleting"
            
    elif symbol_type == "function":
        if symbol.startswith("_"):
            action = FixAction.DELETE
            action_reason = "Private function never called"
            proposed_fix = "Delete function or add # noqa: vulture if intentional"
        else:
            action = FixAction.REVIEW
            action_reason = "Public function may be imported elsewhere"
            
    elif symbol_type == "class_attribute":
        action = FixAction.DELETE
        action_reason = "Class attribute defined but never accessed"
        proposed_fix = "Remove attribute or wire up to functionality"
        
    elif symbol_type == "dead_branch":
        action = FixAction.DELETE
        action_reason = "Unreachable code after return/raise"
        auto_fixable = True
        proposed_fix = "Remove unreachable code"
    
    # Adjust confidence based on thresholds
    base_confidence = CONFIDENCE_THRESHOLDS.get(symbol_type, 0.70)
    adjusted_confidence = min(confidence, base_confidence)
    
    return CategorizedFinding(
        file=file_path,
        line=finding.get("line", 0),
        symbol=symbol,
        symbol_type=symbol_type,
        confidence=adjusted_confidence,
        source=finding.get("source", ""),
        message=finding.get("message", ""),
        context=finding.get("context", ""),
        risk_level=risk_level,
        action=action,
        action_reason=action_reason,
        auto_fixable=auto_fixable,
        test_needed=test_needed,
        proposed_fix=proposed_fix,
    )


# =============================================================================
# MAIN CATEGORIZATION FUNCTION
# =============================================================================

def categorize_dead_code(
    resolved_file: Path,
    repo_root: Path = REPO_ROOT,
    output_file: Optional[Path] = None,
) -> CategorizationResult:
    """
    Categorize resolved findings by risk and action.
    
    Args:
        resolved_file: Path to Phase 2 JSON output
        repo_root: Repository root path
        output_file: Optional output file for JSON results
    
    Returns:
        CategorizationResult with categorized findings
    """
    logger.info(f"Loading resolved findings from {resolved_file}...")
    
    with open(resolved_file) as f:
        resolved_data = json.load(f)
    
    # Filter out false positives
    findings = [
        f for f in resolved_data.get("resolved_findings", [])
        if not f.get("is_false_positive", False)
    ]
    
    logger.info(f"Categorizing {len(findings)} findings...")
    
    result = CategorizationResult(total_findings=len(findings))
    
    for finding in findings:
        categorized = categorize_finding(finding)
        
        # Sort by risk level
        if categorized.risk_level == RiskLevel.HIGH:
            result.high_risk.append(categorized)
        elif categorized.risk_level == RiskLevel.MEDIUM:
            result.medium_risk.append(categorized)
        else:
            result.low_risk.append(categorized)
        
        # Count auto-fixable and manual review
        if categorized.auto_fixable:
            result.auto_fixable_count += 1
        if categorized.action == FixAction.REVIEW:
            result.manual_review_count += 1
    
    # Sort by confidence within each risk level
    result.high_risk.sort(key=lambda x: -x.confidence)
    result.medium_risk.sort(key=lambda x: -x.confidence)
    result.low_risk.sort(key=lambda x: -x.confidence)
    
    logger.info(f"HIGH risk: {len(result.high_risk)}")
    logger.info(f"MEDIUM risk: {len(result.medium_risk)}")
    logger.info(f"LOW risk: {len(result.low_risk)}")
    logger.info(f"Auto-fixable: {result.auto_fixable_count}")
    logger.info(f"Manual review: {result.manual_review_count}")
    
    # Output results
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(result.to_dict(), indent=2))
        logger.info(f"Results written to {output_file}")
    
    return result


def generate_markdown_report(result: CategorizationResult, output_file: Path):
    """Generate a human-readable markdown report."""
    lines = [
        "# Dead Code Audit - Risk Matrix Report",
        "",
        f"**Total Findings:** {result.total_findings}",
        f"**Auto-fixable:** {result.auto_fixable_count}",
        f"**Manual Review Required:** {result.manual_review_count}",
        "",
        "---",
        "",
    ]
    
    # HIGH RISK
    lines.append("## 🔴 HIGH RISK")
    lines.append("")
    if result.high_risk:
        lines.append("| File | Symbol | Type | Confidence | Action | Proposed Fix |")
        lines.append("|------|--------|------|------------|--------|--------------|")
        for f in result.high_risk:
            lines.append(
                f"| `{f.file}:{f.line}` | `{f.symbol}` | {f.symbol_type} | "
                f"{f.confidence:.0%} | {f.action.value} | {f.proposed_fix[:50]}... |"
            )
    else:
        lines.append("*No high risk findings*")
    lines.append("")
    
    # MEDIUM RISK
    lines.append("## 🟡 MEDIUM RISK")
    lines.append("")
    if result.medium_risk:
        lines.append("| File | Symbol | Type | Confidence | Action |")
        lines.append("|------|--------|------|------------|--------|")
        for f in result.medium_risk[:20]:  # Limit to 20
            lines.append(
                f"| `{f.file}:{f.line}` | `{f.symbol}` | {f.symbol_type} | "
                f"{f.confidence:.0%} | {f.action.value} |"
            )
        if len(result.medium_risk) > 20:
            lines.append(f"| ... | *{len(result.medium_risk) - 20} more* | ... | ... | ... |")
    else:
        lines.append("*No medium risk findings*")
    lines.append("")
    
    # LOW RISK
    lines.append("## 🟢 LOW RISK")
    lines.append("")
    if result.low_risk:
        lines.append(f"*{len(result.low_risk)} low-risk findings (unused imports, variables, etc.)*")
        lines.append("")
        lines.append("**Summary by type:**")
        by_type: dict[str, int] = {}
        for f in result.low_risk:
            by_type[f.symbol_type] = by_type.get(f.symbol_type, 0) + 1
        for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"- {t}: {count}")
    else:
        lines.append("*No low risk findings*")
    lines.append("")
    
    # Action Summary
    lines.append("## 📋 Action Summary")
    lines.append("")
    actions: dict[str, int] = {}
    for f in result.high_risk + result.medium_risk + result.low_risk:
        actions[f.action.value] = actions.get(f.action.value, 0) + 1
    
    lines.append("| Action | Count | Description |")
    lines.append("|--------|-------|-------------|")
    action_descriptions = {
        "WIRE_UP": "Connect config to functionality",
        "DELETE": "Remove dead code",
        "NOQA": "Add noqa comment",
        "REVIEW": "Manual review required",
        "AUTO_FIX": "Can be auto-fixed by ruff",
    }
    for action, count in sorted(actions.items(), key=lambda x: -x[1]):
        desc = action_descriptions.get(action, "")
        lines.append(f"| {action} | {count} | {desc} |")
    
    output_file.write_text("\n".join(lines))


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="L9 Dead Code Audit - Phase 3: Categorization")
    parser.add_argument(
        "--input",
        type=str,
        default="reports/dead_code_resolved.json",
        help="Input file from Phase 2",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/dead_code_risk_matrix.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--markdown",
        type=str,
        default="reports/dead_code_risk_matrix.md",
        help="Output markdown file path",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(0),
        )
    
    input_file = REPO_ROOT / args.input
    output_file = REPO_ROOT / args.output
    markdown_file = REPO_ROOT / args.markdown
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print("Run Phase 2 first: python scripts/audit/resolve_dead_code_refs.py")
        return 1
    
    result = categorize_dead_code(
        resolved_file=input_file,
        repo_root=REPO_ROOT,
        output_file=output_file,
    )
    
    # Generate markdown report
    generate_markdown_report(result, markdown_file)
    
    # Print summary
    print("\n" + "=" * 60)
    print("DEAD CODE AUDIT - PHASE 3 CATEGORIZATION")
    print("=" * 60)
    print(f"Total findings: {result.total_findings}")
    print(f"\n🔴 HIGH risk: {len(result.high_risk)}")
    print(f"🟡 MEDIUM risk: {len(result.medium_risk)}")
    print(f"🟢 LOW risk: {len(result.low_risk)}")
    print(f"\n✅ Auto-fixable: {result.auto_fixable_count}")
    print(f"👀 Manual review: {result.manual_review_count}")
    
    print(f"\nJSON output: {output_file}")
    print(f"Markdown report: {markdown_file}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-014",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "cli", "data-models", "dataclass", "filesystem", "logging", "messaging", "metrics", "operations", "serialization"],
    "keywords": ["action", "categorization", "categorize", "categorized", "dead", "finding", "fix", "generate"],
    "business_value": "Provides categorize dead code components including RiskLevel, FixAction, CategorizedFinding",
    "last_modified": "2026-01-14T15:03:00Z",
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
