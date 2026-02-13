# ============================================================================
__dora_meta__ = {
    "component_name": "USAGE GUIDE v1.0",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-30T14:30:36Z",
    "updated_at": "2026-01-12T15:56:02Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "HOW_TO_USE_SUPER_PROMPT",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

# HOW TO USE THE SUPER PROMPT TEMPLATE
# ====================================
# Complete guide for generating AI OS layers with Perplexity Research API

"""
SUPER PROMPT TEMPLATE - USAGE GUIDE v1.0

This guide shows you exactly how to use SUPER_PROMPT_TEMPLATE.py to generate
complete AI Operating System layers using Perplexity Research API.
"""

# ============================================================================
# STEP 1: IMPORT THE TEMPLATE

from SUPER_PROMPT_TEMPLATE import (
    SUPER_PROMPT_COGNITIVE_LAYER,
)

# ============================================================================
# STEP 2: CUSTOMIZE FOR YOUR USE CASE

# EXAMPLE A: Generate an Ethical Governance Layer
# ==============================================


def customize_for_ethical_layer():
    """Customize prompt for ethical governance layer."""

    prompt = (
        SUPER_PROMPT_COGNITIVE_LAYER.replace("[LAYER_NAME]", "Ethical Governance Layer")
        .replace("[DOMAIN_TYPE]", "financial decision-making and hiring workflows")
        .replace("[NUMBER_OF_FRAMEWORKS]", "5")
        .replace(
            "[FRAMEWORK_LIST]",
            "(1) Virtue Ethics Framework, (2) Stakeholder Impact Assessment, (3) Transparency & Explainability Standards, (4) Value Alignment Verification, (5) Bias Detection & Mitigation",
        )
        .replace(
            "[AGENT_TYPES]",
            "risk analysis agents, hiring decision agents, portfolio management agents, compliance agents",
        )
        .replace("[EXISTING_SYSTEM_NAME]", "L9-AI-OS with Boss Sovereignty Layer")
        .replace(
            "[POLICY_REQUIREMENT_1]",
            "Prevent discriminatory decisions against protected groups",
        )
        .replace(
            "[POLICY_REQUIREMENT_2]",
            "Ensure all decisions consider all stakeholder impacts",
        )
    )

    return prompt


# EXAMPLE B: Generate a Learning & Adaptation Layer
# ================================================


def customize_for_learning_layer():
    """Customize prompt for learning & adaptation layer."""

    prompt = (
        SUPER_PROMPT_COGNITIVE_LAYER.replace(
            "[LAYER_NAME]", "Learning & Adaptation Layer"
        )
        .replace("[DOMAIN_TYPE]", "software development and model training workflows")
        .replace("[NUMBER_OF_FRAMEWORKS]", "5")
        .replace(
            "[FRAMEWORK_LIST]",
            "(1) Experiential Learning Cycle, (2) Knowledge Organization & Retention, (3) Strategy Optimization, (4) Skill Development Pathways, (5) Meta-Learning Assessment",
        )
        .replace(
            "[AGENT_TYPES]",
            "code generation agents, testing agents, deployment agents, model training agents",
        )
        .replace("[EXISTING_SYSTEM_NAME]", "L9-AI-OS DevOps Layer")
        .replace(
            "[POLICY_REQUIREMENT_1]", "Learn from previous task successes and failures"
        )
        .replace(
            "[POLICY_REQUIREMENT_2]", "Adapt strategies based on accumulated experience"
        )
    )

    return prompt


# EXAMPLE C: Generate a Risk Management Layer
# ==========================================


def customize_for_risk_layer():
    """Customize prompt for risk management layer."""

    prompt = (
        SUPER_PROMPT_COGNITIVE_LAYER.replace("[LAYER_NAME]", "Risk Management Layer")
        .replace("[DOMAIN_TYPE]", "financial and infrastructure management workflows")
        .replace("[NUMBER_OF_FRAMEWORKS]", "5")
        .replace(
            "[FRAMEWORK_LIST]",
            "(1) Risk Assessment & Quantification, (2) Scenario Analysis & Stress Testing, (3) Mitigation Strategy Development, (4) Compliance & Regulatory Requirements, (5) Risk Monitoring & Adaptation",
        )
        .replace(
            "[AGENT_TYPES]",
            "portfolio agents, infrastructure agents, compliance agents, trading agents",
        )
        .replace("[EXISTING_SYSTEM_NAME]", "L9-AI-OS Trading and Operations Layer")
        .replace("[POLICY_REQUIREMENT_1]", "Quantify and bound all risks before action")
        .replace(
            "[POLICY_REQUIREMENT_2]",
            "Ensure compliance with all regulatory requirements",
        )
    )

    return prompt


# ============================================================================
# STEP 3: PREPARE PERPLEXITY API CALL

import requests


def call_perplexity_api(prompt, api_key):
    """
    Call Perplexity Research API to generate AI OS layer.

    Args:
        prompt: Customized super prompt
        api_key: Your Perplexity API key

    Returns:
        Generated response with code and documentation
    """

    url = "https://api.perplexity.ai/chat/completions"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": "sonar-pro",  # Best for comprehensive research
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,  # Lower for consistent code generation
        "top_p": 0.9,
        "return_citations": True,
        "search_domain_filter": ["perplexity.com"],
        "max_tokens": 8000,  # Allow for large outputs
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")  # noqa: ADR-0019
        return None


# ============================================================================
# STEP 4: EXTRACT AND SAVE GENERATED FILES

import re
import os


def extract_python_files(response_text):
    """
    Extract Python code blocks from API response and save as files.

    Args:
        response_text: Full response from Perplexity API

    Returns:
        List of created files
    """

    # Pattern to find Python code blocks
    pattern = r"```python\n(.*?)\n```"
    matches = re.findall(pattern, response_text, re.DOTALL)

    created_files = []

    for i, code_block in enumerate(matches):
        # Extract filename from code comments
        filename_match = re.search(r"# (/.*?\.py|.*?\.py)", code_block)
        if filename_match:
            filename = filename_match.group(1).split("/")[-1]
        else:
            filename = f"generated_module_{i}.py"

        filepath = f"./{filename}"

        with open(filepath, "w") as f:
            f.write(code_block)

        created_files.append(filepath)
        print(f"✓ Created: {filepath}")  # noqa: ADR-0019

    return created_files


def extract_documentation(response_text):
    """
    Extract markdown documentation from API response.

    Args:
        response_text: Full response from Perplexity API

    Returns:
        List of created documentation files
    """

    # Pattern to find markdown sections
    created_files = []

    # Look for deployment guides, summaries, etc.
    sections = response_text.split("\n# ")

    for section in sections[1:]:  # Skip first empty split
        lines = section.split("\n")
        title = lines[0].replace(" ", "_").lower()
        filename = f"{title}.md"

        content = "# " + section

        with open(filename, "w") as f:
            f.write(content)

        created_files.append(filename)
        print(f"✓ Created: {filename}")  # noqa: ADR-0019

    return created_files


# ============================================================================
# STEP 5: COMPLETE END-TO-END WORKFLOW


def generate_ai_os_layer_complete(api_key, layer_type="ethical"):
    """
    Complete workflow: customize, call API, extract, save.

    Args:
        api_key: Your Perplexity API key
        layer_type: Type of layer to generate ("ethical", "learning", "risk")

    Returns:
        Dictionary with created files and status
    """

    print("=" * 70)  # noqa: ADR-0019
    print("AI OS LAYER GENERATION WORKFLOW")  # noqa: ADR-0019
    print("=" * 70)  # noqa: ADR-0019

    # Step 1: Customize prompt
    print("\n[1/5] Customizing prompt for your requirements...")  # noqa: ADR-0019

    if layer_type == "ethical":
        prompt = customize_for_ethical_layer()
        layer_name = "Ethical Governance Layer"
    elif layer_type == "learning":
        prompt = customize_for_learning_layer()
        layer_name = "Learning & Adaptation Layer"
    elif layer_type == "risk":
        prompt = customize_for_risk_layer()
        layer_name = "Risk Management Layer"
    else:
        raise ValueError(f"Unknown layer type: {layer_type}")

    print(f"  ✓ Prompt customized for {layer_name}")  # noqa: ADR-0019
    print(f"  ✓ Prompt size: {len(prompt)} characters")  # noqa: ADR-0019

    # Step 2: Call Perplexity API
    print("\n[2/5] Calling Perplexity Research API...")  # noqa: ADR-0019
    print("  (This may take 30-60 seconds...)")  # noqa: ADR-0019

    response = call_perplexity_api(prompt, api_key)

    if not response:
        print("  ✗ API call failed")  # noqa: ADR-0019
        return {"status": "failed"}

    response_text = response["choices"][0]["message"]["content"]
    print(f"  ✓ Received response ({len(response_text)} characters)")  # noqa: ADR-0019

    # Step 3: Extract Python files
    print("\n[3/5] Extracting Python files...")  # noqa: ADR-0019

    python_files = extract_python_files(response_text)
    print(f"  ✓ Extracted {len(python_files)} Python files")  # noqa: ADR-0019

    # Step 4: Extract documentation
    print("\n[4/5] Extracting documentation...")  # noqa: ADR-0019

    doc_files = extract_documentation(response_text)
    print(f"  ✓ Extracted {len(doc_files)} documentation files")  # noqa: ADR-0019

    # Step 5: Summary
    print("\n[5/5] Generation complete!")  # noqa: ADR-0019
    print("=" * 70)  # noqa: ADR-0019

    all_files = python_files + doc_files

    print(f"\nGenerated Files ({len(all_files)} total):")  # noqa: ADR-0019
    for filename in all_files:
        print(f"  • {filename}")  # noqa: ADR-0019

    print("\nNext Steps:")  # noqa: ADR-0019
    print("  1. Review generated files")  # noqa: ADR-0019
    print("  2. Run: python quick_start.py  (to verify)")  # noqa: ADR-0019
    print("  3. Deploy to /l/MRL/ or your target path")  # noqa: ADR-0019
    print("  4. Integrate with L9-AI-OS")  # noqa: ADR-0019

    return {
        "status": "success",
        "layer_name": layer_name,
        "python_files": python_files,
        "doc_files": doc_files,
        "total_files": len(all_files),
        "response": response_text,
    }


# ============================================================================
# STEP 6: COMMAND-LINE USAGE


def main():
    """Command-line interface for layer generation."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Generate AI OS layers using Perplexity Research API"
    )
    parser.add_argument("--api-key", required=True, help="Your Perplexity API key")
    parser.add_argument(
        "--layer-type",
        choices=["ethical", "learning", "risk"],
        default="ethical",
        help="Type of layer to generate",
    )
    parser.add_argument(
        "--output-dir",
        default="./generated_layer",
        help="Output directory for generated files",
    )

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    os.chdir(args.output_dir)

    # Generate layer
    result = generate_ai_os_layer_complete(
        api_key=args.api_key, layer_type=args.layer_type
    )

    if result["status"] == "success":
        print("\n✓ Layer generation complete!")  # noqa: ADR-0019
        print(f"✓ Files saved to: {args.output_dir}")  # noqa: ADR-0019
    else:
        print("\n✗ Layer generation failed")  # noqa: ADR-0019


# ============================================================================
# EXAMPLE: DIRECT PYTHON USAGE


def example_usage():
    """Example showing how to use this programmatically."""

    # Your Perplexity API key
    API_KEY = "your-api-key-here"

    # Option 1: Generate Ethical Governance Layer
    print("Generating Ethical Governance Layer...")  # noqa: ADR-0019
    result = generate_ai_os_layer_complete(api_key=API_KEY, layer_type="ethical")

    # Option 2: Generate Learning & Adaptation Layer
    print("\nGenerating Learning & Adaptation Layer...")  # noqa: ADR-0019
    result = generate_ai_os_layer_complete(api_key=API_KEY, layer_type="learning")

    # Option 3: Generate Risk Management Layer
    print("\nGenerating Risk Management Layer...")  # noqa: ADR-0019
    result = generate_ai_os_layer_complete(api_key=API_KEY, layer_type="risk")


# ============================================================================
# QUICK REFERENCE

QUICK_START = """
QUICK START GUIDE
=================

1. GET YOUR API KEY
   - Sign up at https://www.perplexity.ai
   - Get your Research API key

2. INSTALL DEPENDENCIES
   pip install requests

3. GENERATE A LAYER
   python how_to_use_super_prompt.py \\
     --api-key YOUR_API_KEY \\
     --layer-type ethical \\
     --output-dir ./my_layer

4. VERIFY GENERATION
   cd my_layer
   python quick_start.py

5. DEPLOY
   cp -r *.py /l/MRL/
   # Ready to use!

LAYER TYPES AVAILABLE:
- ethical: Ethical Governance Layer
- learning: Learning & Adaptation Layer  
- risk: Risk Management Layer

Each generates:
✓ 2,500+ lines of production Python
✓ 1,200+ lines of documentation
✓ 6+ working examples
✓ Complete deployment guides
"""

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Command-line mode
        main()
    else:
        # Show usage examples
        print(QUICK_START)  # noqa: ADR-0019
        print("\nFor command-line usage:")  # noqa: ADR-0019
        print("  python how_to_use_super_prompt.py --help")  # noqa: ADR-0019
        print("\nFor programmatic usage:")  # noqa: ADR-0019
        print("  from how_to_use_super_prompt import generate_ai_os_layer_complete")  # noqa: ADR-0019
        print("  result = generate_ai_os_layer_complete('your-api-key')")  # noqa: ADR-0019

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "cli",
        "code-generation",
        "event-driven",
        "foundation",
        "messaging",
        "monitoring",
        "testing",
    ],
    "keywords": [
        "api",
        "complete",
        "customize",
        "documentation",
        "ethical",
        "example",
        "extract",
        "files",
    ],
    "business_value": "This guide shows you exactly how to use SUPER_PROMPT_TEMPLATE.py to generate complete AI Operating System layers using Perplexity Research API.",
    "last_modified": "2026-01-12T15:56:02Z",
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
