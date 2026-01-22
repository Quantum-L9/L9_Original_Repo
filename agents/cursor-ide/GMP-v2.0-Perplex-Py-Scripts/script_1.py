# Generate complete GMP v2.0 file structure
gmp_v2_files = {
    "GMP-System-Prompt-v2.0.md": "System Prompt - Core instructions",
    "GMP-Action-Prompt-Canonical-v2.0.md": "Action Prompt - Execute TODO plans",
    "GMP-Audit-Prompt-Canonical-v2.0.md": "Audit Prompt - Validate executions",
    "GMP-Action-Prompt-Generator-v2.0.md": "Generator - Create action prompts",
    "GMP-Audit-Prompt-Guide-v2.0.md": "Audit Guide - How to audit",
    "L9_Cursor-Integration-Protocol-v2.0.md": "L9xCIP - Cursor protocol",
    "Cursor-Directive-v2.0.md": "Cursor behavioral rules",
    "DORA-Block-Spec-v2.0.md": "DORA metadata specification",
}

# File naming and versioning strategy
versioning_strategy = """
GMP v2.0 VERSIONING STRATEGY
═══════════════════════════════════════════════════════════

SEMANTIC VERSIONING (semver.org)
- Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
- Examples: 2.0.0, 2.1.0-beta.1, 2.0.1+20251225

VERSION INCREMENT RULES:
1. MAJOR (x.0.0): Breaking changes
   - TODO format changes
   - Phase structure changes
   - Report section changes
   - Non-backward-compatible modifications

2. MINOR (x.y.0): Additive features
   - New phases added
   - New validation checks
   - New checklist items
   - Backward-compatible enhancements

3. PATCH (x.y.z): Bug fixes & clarifications
   - Typo corrections
   - Clarifications (no behavior change)
   - Documentation improvements
   - Performance optimizations (no API change)

4. PRE-RELEASE (x.y.z-alpha|beta|rc.n):
   - alpha: Internal testing only
   - beta: External testing, feature-complete
   - rc: Release candidate, production-ready candidate

FILE NAMING CONVENTION:
- Pattern: GMP-{Component}-v{MAJOR}.{MINOR}.{PATCH}.md
- Examples:
  * GMP-System-Prompt-v2.0.0.md
  * GMP-Action-Prompt-Canonical-v2.1.0.md
  * GMP-Audit-Prompt-Canonical-v2.0.1.md

MIGRATION POLICY:
- v1.x → v2.0: Breaking changes require migration guide
- v2.0 → v2.1: Backward compatible, no migration needed
- Deprecation: Min 2 minor versions before removal
"""

print(versioning_strategy)
print("\n" + "=" * 60)
print("GMP v2.0 FILE MANIFEST:")
print("=" * 60)
for filename, description in gmp_v2_files.items():
    print(f"✓ {filename}")
    print(f"  {description}\n")
