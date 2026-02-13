#!/usr/bin/env python3
"""
L9 QC Dashboard
===============
Review and approve/reject extracted concepts before generating PLAN specs.

Features:
- Interactive CLI dashboard
- Review extracted concepts
- Approve/reject/edit concepts
- Batch operations
- Generate PLAN specs for approved concepts

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Qc Dashboard",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-20T18:47:58Z",
    "updated_at": "2026-01-20T23:43:16Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "l9_qc_dashboard",
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
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC
from pathlib import Path

import yaml


@dataclass
class ConceptReview:
    """Review status for a concept."""

    concept_id: str
    status: str  # pending, approved, rejected, edited
    reviewer_notes: str
    reviewed_at: str


class QCDashboard:
    """Interactive dashboard for concept review."""

    def __init__(self, harvested_dir: Path):
        """
        Initialize the QC dashboard.

        Args:
            harvested_dir: Directory with harvested concepts
        """
        self.harvested_dir = Path(harvested_dir)
        self.concepts_dir = self.harvested_dir / "concepts"
        self.yaml_dir = self.harvested_dir / "yaml_specs"
        self.reviews_dir = self.harvested_dir / "reviews"
        self.approved_dir = self.harvested_dir / "approved"

        self.reviews_dir.mkdir(exist_ok=True)
        self.approved_dir.mkdir(exist_ok=True)

        self.concepts = self._load_concepts()
        self.reviews = self._load_reviews()

    def _load_concepts(self) -> list[dict]:
        """Load all extracted concepts."""
        concepts = []

        if not self.concepts_dir.exists():
            return concepts

        for concept_file in self.concepts_dir.glob("*.json"):
            with open(concept_file) as f:
                concept = json.load(f)
                concepts.append(concept)

        return sorted(concepts, key=lambda x: -x["confidence"])

    def _load_reviews(self) -> dict[str, ConceptReview]:
        """Load existing reviews."""
        reviews = {}

        if not self.reviews_dir.exists():
            return reviews

        for review_file in self.reviews_dir.glob("*.json"):
            with open(review_file) as f:
                review_data = json.load(f)
                review = ConceptReview(**review_data)
                reviews[review.concept_id] = review

        return reviews

    def _save_review(self, review: ConceptReview):
        """Save a review."""
        review_file = self.reviews_dir / f"{review.concept_id}.json"
        with open(review_file, "w") as f:
            json.dump(asdict(review), f, indent=2)

        self.reviews[review.concept_id] = review

    def run(self):
        """Run the interactive dashboard."""
        while True:
            self._clear_screen()
            self._show_header()
            self._show_stats()
            self._show_menu()

            choice = input("\n👉 Select option: ").strip()

            if choice == "1":
                self._review_concepts()
            elif choice == "2":
                self._show_approved()
            elif choice == "3":
                self._show_rejected()
            elif choice == "4":
                self._batch_approve()
            elif choice == "5":
                self._generate_plan_specs()
            elif choice == "6":
                self._export_summary()
            elif choice == "q":
                print("\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid option")
                input("Press Enter to continue...")

    def _clear_screen(self):
        """Clear the terminal screen."""
        print("\033[2J\033[H", end="")

    def _show_header(self):
        """Show dashboard header."""
        print("=" * 80)
        print(" " * 25 + "L9 QC DASHBOARD")
        print("=" * 80)

    def _show_stats(self):
        """Show concept statistics."""
        total = len(self.concepts)
        approved = sum(1 for r in self.reviews.values() if r.status == "approved")
        rejected = sum(1 for r in self.reviews.values() if r.status == "rejected")
        pending = total - approved - rejected

        print("\n📊 Concept Statistics:")
        print(f"   Total: {total}")
        print(f"   ✅ Approved: {approved}")
        print(f"   ❌ Rejected: {rejected}")
        print(f"   ⏳ Pending: {pending}")

    def _show_menu(self):
        """Show main menu."""
        print("\n📋 Menu:")
        print("   1. Review concepts")
        print("   2. Show approved concepts")
        print("   3. Show rejected concepts")
        print("   4. Batch approve high-confidence concepts")
        print("   5. Generate PLAN specs for approved concepts")
        print("   6. Export summary report")
        print("   q. Quit")

    def _review_concepts(self):
        """Review concepts interactively."""
        pending_concepts = [
            c
            for c in self.concepts
            if c["concept_id"] not in self.reviews
            or self.reviews[c["concept_id"]].status == "pending"
        ]

        if not pending_concepts:
            print("\n✅ No pending concepts to review!")
            input("Press Enter to continue...")
            return

        for i, concept in enumerate(pending_concepts):
            self._clear_screen()
            print(f"\n📄 Reviewing Concept {i + 1}/{len(pending_concepts)}")
            print("=" * 80)

            self._show_concept(concept)

            print("\n🎯 Actions:")
            print("   a - Approve")
            print("   r - Reject")
            print("   e - Edit YAML")
            print("   s - Skip")
            print("   q - Back to menu")

            action = input("\n👉 Action: ").strip().lower()

            if action == "a":
                self._approve_concept(concept)
            elif action == "r":
                self._reject_concept(concept)
            elif action == "e":
                self._edit_concept(concept)
            elif action == "s":
                continue
            elif action == "q":
                break

    def _show_concept(self, concept: dict):
        """Display concept details."""
        print(f"\n📌 Concept: {concept['concept_name']}")
        print(f"📁 Source: {Path(concept['source_file']).name}")
        print(f"🏷️  Category: {concept['category']}")
        print(f"📊 Confidence: {concept['confidence']:.2f}")
        print("\n📝 Description:")
        print(f"   {concept['description']}")

        # Show YAML spec
        yaml_file = self.yaml_dir / f"{concept['concept_name']}.yaml"
        if yaml_file.exists():
            with open(yaml_file) as f:
                yaml_data = yaml.safe_load(f)

            print("\n📄 Generated YAML:")
            print(f"   Name: {yaml_data.get('CONCEPT_NAME')}")
            print(f"   Version: {yaml_data.get('VERSION')}")
            print(f"   One-sentence: {yaml_data.get('ONE_SENTENCE', '')[:100]}...")

            if yaml_data.get("ARCHITECTURE", {}).get("components"):
                print(f"   Components: {len(yaml_data['ARCHITECTURE']['components'])}")

    def _approve_concept(self, concept: dict):
        """Approve a concept."""
        notes = input("📝 Review notes (optional): ").strip()

        from datetime import datetime

        review = ConceptReview(
            concept_id=concept["concept_id"],
            status="approved",
            reviewer_notes=notes,
            reviewed_at=datetime.now(UTC).isoformat() + "Z",
        )

        self._save_review(review)

        # Copy YAML to approved directory
        yaml_file = self.yaml_dir / f"{concept['concept_name']}.yaml"
        if yaml_file.exists():
            approved_file = self.approved_dir / yaml_file.name
            approved_file.write_text(yaml_file.read_text())

        print("\n✅ Concept approved!")
        input("Press Enter to continue...")

    def _reject_concept(self, concept: dict):
        """Reject a concept."""
        reason = input("❌ Rejection reason: ").strip()

        from datetime import datetime

        review = ConceptReview(
            concept_id=concept["concept_id"],
            status="rejected",
            reviewer_notes=reason,
            reviewed_at=datetime.now(UTC).isoformat() + "Z",
        )

        self._save_review(review)

        print("\n❌ Concept rejected!")
        input("Press Enter to continue...")

    def _edit_concept(self, concept: dict):
        """Edit concept YAML."""
        yaml_file = self.yaml_dir / f"{concept['concept_name']}.yaml"

        if not yaml_file.exists():
            print("❌ YAML file not found!")
            input("Press Enter to continue...")
            return

        # Open in default editor
        editor = os.environ.get("EDITOR", "nano")
        subprocess.call([editor, str(yaml_file)])

        # Mark as edited
        from datetime import datetime

        review = ConceptReview(
            concept_id=concept["concept_id"],
            status="edited",
            reviewer_notes="Manually edited YAML",
            reviewed_at=datetime.now(UTC).isoformat() + "Z",
        )

        self._save_review(review)

        print("\n✏️  Concept edited!")
        input("Press Enter to continue...")

    def _show_approved(self):
        """Show approved concepts."""
        approved = [
            c
            for c in self.concepts
            if self.reviews.get(
                c["concept_id"], ConceptReview("", "pending", "", "")
            ).status
            == "approved"
        ]

        self._clear_screen()
        print("\n✅ Approved Concepts")
        print("=" * 80)

        if not approved:
            print("\nNo approved concepts yet.")
        else:
            print("\n| # | Concept | Category | Confidence |")
            print("|---|---------|----------|------------|")
            for i, concept in enumerate(approved, 1):
                name = concept["concept_name"][:30]
                cat = concept["category"]
                conf = concept["confidence"]
                print(f"| {i} | {name} | {cat} | {conf:.2f} |")

        input("\nPress Enter to continue...")

    def _show_rejected(self):
        """Show rejected concepts."""
        rejected = [
            c
            for c in self.concepts
            if self.reviews.get(
                c["concept_id"], ConceptReview("", "pending", "", "")
            ).status
            == "rejected"
        ]

        self._clear_screen()
        print("\n❌ Rejected Concepts")
        print("=" * 80)

        if not rejected:
            print("\nNo rejected concepts yet.")
        else:
            for i, concept in enumerate(rejected, 1):
                review = self.reviews[concept["concept_id"]]
                print(f"\n{i}. {concept['concept_name']}")
                print(f"   Reason: {review.reviewer_notes}")

        input("\nPress Enter to continue...")

    def _batch_approve(self):
        """Batch approve high-confidence concepts."""
        threshold = float(input("📊 Minimum confidence (0.0-1.0): ").strip() or "0.8")

        high_conf = [
            c
            for c in self.concepts
            if c["confidence"] >= threshold and c["concept_id"] not in self.reviews
        ]

        if not high_conf:
            print(f"\n❌ No concepts with confidence >= {threshold}")
            input("Press Enter to continue...")
            return

        print(f"\n📋 Found {len(high_conf)} concepts with confidence >= {threshold}")
        confirm = input("✅ Approve all? (y/n): ").strip().lower()

        if confirm == "y":
            from datetime import datetime

            for concept in high_conf:
                review = ConceptReview(
                    concept_id=concept["concept_id"],
                    status="approved",
                    reviewer_notes=f"Batch approved (confidence >= {threshold})",
                    reviewed_at=datetime.now(UTC).isoformat() + "Z",
                )
                self._save_review(review)

                # Copy to approved
                yaml_file = self.yaml_dir / f"{concept['concept_name']}.yaml"
                if yaml_file.exists():
                    approved_file = self.approved_dir / yaml_file.name
                    approved_file.write_text(yaml_file.read_text())

            print(f"\n✅ Approved {len(high_conf)} concepts!")
        else:
            print("\n❌ Batch approval cancelled")

        input("Press Enter to continue...")

    def _generate_plan_specs(self):
        """Generate PLAN specs for approved concepts."""
        approved = [
            c
            for c in self.concepts
            if self.reviews.get(
                c["concept_id"], ConceptReview("", "pending", "", "")
            ).status
            == "approved"
        ]

        if not approved:
            print("\n❌ No approved concepts to generate PLAN specs for!")
            input("Press Enter to continue...")
            return

        print(f"\n📋 Found {len(approved)} approved concepts")
        confirm = input("🚀 Generate PLAN specs for all? (y/n): ").strip().lower()

        if confirm != "y":
            print("\n❌ Cancelled")
            input("Press Enter to continue...")
            return

        # Import spec generator
        import sys

        sys.path.insert(0, str(Path(__file__).parent))
        from l9_spec_generator import L9SpecGenerator

        generator = L9SpecGenerator(output_dir=self.harvested_dir / "plan_specs")

        for concept in approved:
            yaml_file = self.approved_dir / f"{concept['concept_name']}.yaml"
            if yaml_file.exists():
                try:
                    print(f"  Generating PLAN for: {concept['concept_name']}...")
                    generator.generate_from_file(yaml_file)
                except Exception as e:
                    print(f"    ❌ Error: {e}")

        print("\n✅ PLAN specs generated!")
        print(f"📁 Location: {self.harvested_dir / 'plan_specs'}")
        input("Press Enter to continue...")

    def _export_summary(self):
        """Export summary report."""
        summary = "# QC Review Summary\n\n"

        from datetime import datetime

        summary += f"**Generated:** {datetime.now(UTC).isoformat()}Z\n\n"

        approved = [
            c
            for c in self.concepts
            if self.reviews.get(
                c["concept_id"], ConceptReview("", "pending", "", "")
            ).status
            == "approved"
        ]
        rejected = [
            c
            for c in self.concepts
            if self.reviews.get(
                c["concept_id"], ConceptReview("", "pending", "", "")
            ).status
            == "rejected"
        ]
        pending = [c for c in self.concepts if c["concept_id"] not in self.reviews]

        summary += f"**Total Concepts:** {len(self.concepts)}\n"
        summary += f"**Approved:** {len(approved)}\n"
        summary += f"**Rejected:** {len(rejected)}\n"
        summary += f"**Pending:** {len(pending)}\n\n"

        summary += "## Approved Concepts\n\n"
        summary += "| Concept | Category | Confidence |\n"
        summary += "|---------|----------|------------|\n"
        for concept in approved:
            summary += f"| {concept['concept_name']} | {concept['category']} | {concept['confidence']:.2f} |\n"

        summary_file = self.harvested_dir / "QC_SUMMARY.md"
        summary_file.write_text(summary)

        print(f"\n✅ Summary exported to: {summary_file}")
        input("Press Enter to continue...")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="L9 QC Dashboard: Review and approve extracted concepts"
    )

    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("./harvested"),
        help="Harvested concepts directory",
    )

    args = parser.parse_args()

    dashboard = QCDashboard(harvested_dir=args.dir)
    dashboard.run()


if __name__ == "__main__":
    import os

    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-035",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "batch-processing",
        "cli",
        "config",
        "current-work",
        "dataclass",
        "filesystem",
        "operations",
        "serialization",
        "subprocess",
    ],
    "keywords": ["concept", "dashboard", "review"],
    "business_value": "Provides l9 qc dashboard components including ConceptReview, QCDashboard",
    "last_modified": "2026-01-20T23:43:16Z",
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
