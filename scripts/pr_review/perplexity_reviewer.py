#!/usr/bin/env python3
"""
Perplexity AI PR Reviewer - AUDIT MODE
Deep security, performance, and architecture analysis
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "AUDIT MODE",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-24T17:18:54Z",
    "updated_at": "2026-01-24T17:18:34Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "perplexity_reviewer",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Neo4j", "Perplexity API", "PostgreSQL", "Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import json
import os
import subprocess
from typing import Any

import requests

PROTECTED_FILES = {
    "api/websocket_orchestrator.py",
    "docker-compose.yml",
    "core/kernel_loader.py",
    "memory/substrate_service.py",
    "core/schemas/packet_envelope.py",
}


class PerplexityAuditor:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.audit_mode = os.getenv("AUDIT_MODE", "full")
        self.base_url = "https://api.perplexity.ai/chat/completions"

    def get_pr_diff(self) -> str:
        """Fetch PR diff"""
        cmd = f"git diff {os.getenv('BASE_SHA')}...{os.getenv('HEAD_SHA')}"
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        return result.stdout

    def get_file_content(self, filepath: str) -> str:
        """Get full file content for deep analysis"""
        try:
            with open(filepath, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""

    def audit_with_perplexity(self, diff: str, files: list[str]) -> dict[str, Any]:
        """Comprehensive security + performance + architecture audit"""

        prompt = f"""You are conducting a DEEP AUDIT of this pull request for the L9 AI agent system.

**Audit Scope** (Priority Order):
1. **Security**: Injection risks, secret exposure, unsafe operations
2. **Performance**: Async patterns, caching opportunities, batch operations
3. **Architecture**: L9 protocol alignment, separation of concerns, scalability
4. **Code Quality**: Type safety, error handling, documentation

**L9 Context**:
- PacketEnvelope protocol for inter-component messaging
- Memory substrates: PostgreSQL, Neo4j, Redis (access via MemorySubstrateService only)
- Governance layer enforces tool usage policies
- Kernel system contains immutable core logic

**Changes**:
```diff
{diff[:20000]}
```

**Audit Deliverables** (JSON format):
{{
  "security_findings": [
    {{"severity": "critical|high|medium|low", "issue": "...", "file": "...", "line": 123, "fix": "...code fix..."}}
  ],
  "performance_opportunities": [
    {{"impact": "high|medium|low", "opportunity": "...", "file": "...", "implementation": "...code example..."}}
  ],
  "architecture_improvements": [
    {{"area": "...", "current_pattern": "...", "recommended_pattern": "...", "benefit": "..."}}
  ],
  "auto_fixes": [
    {{"file": "...", "original": "...", "fixed": "...", "reason": "..."}}
  ],
  "summary": "Overall risk assessment and recommendations"
}}

Return ONLY valid JSON.
"""

        response = requests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-sonar-large-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior security and architecture auditor for frontier AI systems. Focus on production risks, scalability, and L9-specific patterns.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 8000,
            },
            timeout=120,
        )

        if response.status_code != 200:
            print(f"❌ Perplexity API error: {response.status_code}")
            return {"security_findings": [], "summary": "API error"}

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Extract JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return {"security_findings": [], "summary": content}

    def apply_auto_fixes(self, fixes: list[dict]) -> int:
        """Apply security and performance fixes"""
        applied = 0

        for fix in fixes:
            filepath = fix["file"]

            if any(pf in filepath for pf in PROTECTED_FILES):
                print(f"⚠️  Skipping protected file: {filepath}")
                continue

            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()

                if fix["original"] in content:
                    content = content.replace(fix["original"], fix["fixed"])

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)

                    print(f"✅ Applied fix to: {filepath}")
                    print(f"   Reason: {fix['reason']}")
                    applied += 1
            except Exception as e:
                print(f"❌ Failed: {e}")

        return applied

    def generate_audit_report(self, audit: dict) -> str:
        """Generate markdown audit report"""
        md = []

        md.append("### 🛡️ Security Findings\n")
        for finding in audit.get("security_findings", [])[:5]:
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                finding.get("severity", "low"), "⚪"
            )
            md.append(
                f"{emoji} **{finding.get('severity', 'unknown').upper()}**: {finding.get('issue', 'No details')}"
            )
            md.append(
                f"  File: `{finding.get('file', 'unknown')}` (Line {finding.get('line', '?')})\n"
            )

        md.append("\n### ⚡ Performance Opportunities\n")
        for opp in audit.get("performance_opportunities", [])[:5]:
            md.append(
                f"- **{opp.get('opportunity', 'Unknown')}** ({opp.get('impact', 'unknown')} impact)"
            )
            md.append(f"  File: `{opp.get('file', 'unknown')}`\n")

        md.append("\n### 🏗️ Architecture Improvements\n")
        for imp in audit.get("architecture_improvements", [])[:3]:
            md.append(f"- **{imp.get('area', 'Unknown')}**")
            md.append(f"  Benefit: {imp.get('benefit', 'Not specified')}\n")

        md.append(f"\n### 📊 Summary\n{audit.get('summary', 'No summary available')}")

        return "\n".join(md)

    def run(self):
        """Main execution"""
        print("🔍 Starting Perplexity Deep Audit...")

        diff = self.get_pr_diff()

        if not diff:
            print("✅ No changes to audit")
            return

        cmd = f"git diff --name-only {os.getenv('BASE_SHA')}...{os.getenv('HEAD_SHA')}"
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        files = [f.strip() for f in result.stdout.split("\n") if f.strip()]

        print(f"📁 Auditing {len(files)} files...")

        # Run comprehensive audit
        audit = self.audit_with_perplexity(diff, files)

        # Apply auto-fixes
        fixes = audit.get("auto_fixes", [])
        if fixes:
            applied = self.apply_auto_fixes(fixes)
            print(f"\n✅ Applied {applied}/{len(fixes)} security/performance fixes")

        # Generate report
        report = self.generate_audit_report(audit)

        with open("/tmp/perplexity_audit.md", "w") as f:
            f.write(report)

        print("\n" + report)
        print("\n✅ Audit complete")


if __name__ == "__main__":
    auditor = PerplexityAuditor()
    auditor.run()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-012",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "audit-tool",
        "auth",
        "batch-processing",
        "cli",
        "code-quality",
        "filesystem",
        "messaging",
        "operations",
        "realtime",
    ],
    "keywords": [
        "apply",
        "audit",
        "auditor",
        "auto",
        "diff",
        "fixes",
        "generate",
        "mode",
    ],
    "business_value": "Implements PerplexityAuditor for perplexity reviewer functionality",
    "last_modified": "2026-01-24T17:18:34Z",
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
