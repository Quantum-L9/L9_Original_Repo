"""
CodeGen CLI - Command-line interface for Unified CodeGen System

Usage:
    python -m l9.core.codegen.cli generate --input spec.yaml --type agent_yaml --output ./output
    python -m l9.core.codegen.cli validate --files ./output/module_*
    python -m l9.core.codegen.cli research --query "What are best practices for async Python?"

Author: L9 AIOS
Version: 1.0.0
Created: 2025-12-31
"""

import asyncio
from pathlib import Path

import click

from .gatekeeper.codegen_gatekeeper import CodeGenGatekeeperAgent


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Unified CodeGen System - Generate production-ready code from specs"""
    pass


@cli.command()
@click.option(
    "--input", "-i", required=True, type=click.Path(exists=True), help="Input spec file"
)
@click.option(
    "--type",
    "-t",
    required=True,
    type=click.Choice(["agent_yaml", "module_block", "symcode", "concept", "partial"]),
    help="Contract type",
)
@click.option(
    "--output", "-o", required=True, type=click.Path(), help="Output directory"
)
@click.option(
    "--research/--no-research", default=True, help="Enable Perplexity research"
)
@click.option(
    "--min-confidence", default=85.0, type=float, help="Minimum confidence threshold"
)
def generate(input: str, type: str, output: str, research: bool, min_confidence: float):
    """Generate code from a spec file"""

    click.echo("🚀 Unified CodeGen System v1.0.0")
    click.echo(f"📄 Input: {input}")
    click.echo(f"📦 Type: {type}")
    click.echo(f"📂 Output: {output}")
    click.echo(f"🔬 Research: {'enabled' if research else 'disabled'}")
    click.echo(f"🎯 Min Confidence: {min_confidence}%")
    click.echo("")

    # Read input file
    input_path = Path(input)
    contract = input_path.read_text()

    # Initialize gatekeeper
    gatekeeper = CodeGenGatekeeperAgent(
        research_enabled=research, min_confidence=min_confidence
    )

    # Run generation
    async def run():
        """
        Performs the main execution flow for the CodeGen CLI, coordinating task submission and result handling.


        Returns:
            The result of the gatekeeper run, indicating success status and output details.

        Raises:
            Exception: If an error occurs during task execution or result processing.
        """
        result = await gatekeeper.run(
            task={
                "contract": contract,
                "contract_type": type,
                "output_dir": output,
                "research_enabled": research,
            }
        )

        if result.success:
            click.echo("✅ Code generation successful!")
            click.echo(f"📊 Confidence: {result.confidence * 100:.1f}%")
            click.echo(
                f"📁 Files generated: {len(result.data.get('files_generated', []))}"
            )
            click.echo(f"🌿 Git branch: {result.data.get('git_branch')}")
            click.echo(f"📈 Coverage: {result.data.get('coverage')}%")
            click.echo(f"⏱️  Time: {result.data.get('generation_time'):.2f}s")
        else:
            click.echo("❌ Code generation failed!")
            click.echo(f"📊 Confidence: {result.confidence * 100:.1f}%")
            click.echo(f"❗ Reason: {result.data.get('reason', 'Unknown')}")

            if result.metadata.get("gaps"):
                click.echo("\n🔍 Gaps found:")
                for gap in result.metadata["gaps"]:
                    click.echo(f"  - {gap['category']}: {gap['description']}")

    asyncio.run(run())


@cli.command()
@click.option(
    "--files",
    "-f",
    required=True,
    type=click.Path(exists=True),
    help="Directory or file to validate",
)
def validate(files: str):
    """Validate generated code"""

    click.echo(f"🔍 Validating: {files}")

    from .utilities import CodeValidator

    files_path = Path(files)

    if files_path.is_dir():
        file_list = list(files_path.rglob("*.py"))
    else:
        file_list = [files_path]

    validator = CodeValidator()

    async def run():
        """
        Performs the main execution flow of the CodeGen CLI, including validation and reporting.



        Raises:
            Exception: If validation or reporting encounters an error.
        """
        report = await validator.validate_all(file_list, {})

        click.echo("\n📊 Validation Report")
        click.echo(f"{'=' * 60}")
        click.echo(f"Overall Score: {report['overall_score']:.1f}%")
        click.echo(f"Status: {'✅ PASSED' if report['passed'] else '❌ FAILED'}")
        click.echo(f"Coverage: {report['coverage']:.1f}%")
        click.echo("\n🚪 Gates:")

        for gate in report["gates"]:
            status = "✅" if gate["passed"] else "❌"
            click.echo(
                f"  {status} Gate {gate['gate_id']}: {gate['name']} - {gate['score']:.1f}%"
            )

            if gate["errors"]:
                for error in gate["errors"]:
                    click.echo(f"      ❗ {error}")

            if gate["warnings"]:
                for warning in gate["warnings"]:
                    click.echo(f"      ⚠️  {warning}")

    asyncio.run(run())


@cli.command()
@click.option("--query", "-q", required=True, help="Research query")
def research(query: str):
    """Research a topic using Perplexity"""

    click.echo(f"🔬 Researching: {query}")

    from .gatekeeper.codegen_gatekeeper import BlindSpot, CodeGenGatekeeperAgent

    gatekeeper = CodeGenGatekeeperAgent()

    async def run():
        """
        Performs the main execution flow of the CodeGen CLI, managing research blind spot analysis.



        Raises:
            Exception: If an error occurs during blind spot analysis or command execution.
        """
        blind_spot = BlindSpot(
            category="research",
            description=query,
            severity="medium",
            research_query=query,
            confidence=100.0,
        )

        findings = await gatekeeper._research_blind_spots([blind_spot])

        if findings:
            finding = findings[0]
            click.echo("\n📚 Research Results:")
            click.echo(f"{'=' * 60}")
            click.echo(f"\n{finding.answer}")

            if finding.sources:
                click.echo("\n🔗 Sources:")
                for source in finding.sources:
                    click.echo(f"  - {source}")
        else:
            click.echo("❌ No research results found")

    asyncio.run(run())


if __name__ == "__main__":
    cli()
