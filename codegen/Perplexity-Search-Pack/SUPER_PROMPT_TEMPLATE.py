# ============================================================================
__dora_meta__ = {
    "component_name": "Super Prompt Template",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-16T21:54:14Z",
    "updated_at": "2026-01-12T15:56:02Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "SUPER_PROMPT_TEMPLATE",
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

# SUPER PROMPT TEMPLATE FOR GENERATING AI OPERATING SYSTEM LAYERS
# ================================================================
# Use this template with Perplexity Research API to generate complete,
# production-ready Python implementations of cognitive governance layers
# and AI OS components.
#
# USAGE: Replace [BRACKET_VALUES] with your specific requirements
# ================================================================

"""
SUPER PROMPT TEMPLATE v1.0
For Perplexity Research API - AI OS Layer Generation

This template generates:
- Complete Python script packets (2,500+ lines)
- Multi-file modular architectures
- Production-ready implementations
- Comprehensive documentation
- Working examples and quick-start guides
- Integration patterns with existing systems
"""

# ============================================================================
# TEMPLATE: COGNITIVE GOVERNANCE LAYER GENERATION

SUPER_PROMPT_COGNITIVE_LAYER = """
You are an applied research team tasked with designing and implementing a 
[LAYER_NAME] for an AI operating system that orchestrates [DOMAIN_TYPE] 
workflows. The system should integrate [NUMBER_OF_FRAMEWORKS] cognitive/learning 
frameworks: [FRAMEWORK_LIST]. Your goals are to:

(a) Specify how each framework is represented in machine-readable form
(b) Define policies that use these representations to constrain and guide AI agents
(c) Create a production-ready Python implementation
(d) Provide comprehensive documentation and working examples

CONCRETELY:

PART 1: ARCHITECTURE DESIGN
============================

Design the [LAYER_NAME] that sits above task agents [AGENT_TYPES]. For each of 
the [NUMBER_OF_FRAMEWORKS] frameworks, specify:

1. Data structures, tags, or schemas
   - Example: How to represent [FRAMEWORK_1] in machine-readable form
   - Example: How to represent [FRAMEWORK_2] in machine-readable form
   - [CONTINUE FOR EACH FRAMEWORK]

2. Rules by which the layer interprets and enforces them

3. How these rules interact with risk/impact thresholds for actions

4. Integration points with existing [EXISTING_SYSTEM_NAME]

PART 2: MACHINE-READABLE REPRESENTATIONS
=========================================

For each framework:

[FRAMEWORK_1]:
  - Define core enums/classes
  - Specify validation criteria
  - Create example data structures
  - Document thresholds and scoring

[FRAMEWORK_2]:
  - Define core enums/classes
  - Specify validation criteria
  - Create example data structures
  - Document thresholds and scoring

[CONTINUE FOR EACH FRAMEWORK]

PART 3: POLICY DEFINITIONS
===========================

Define machine-readable policies that:
- [POLICY_REQUIREMENT_1]
- [POLICY_REQUIREMENT_2]
- Implement gating based on [FRAMEWORK_1] and [FRAMEWORK_2]
- Escalate decisions when appropriate
- Track all governance decisions

PART 4: PYTHON IMPLEMENTATION
=============================

Create a production-ready Python script packet with:

Core Files (to implement):
  1. [layer_name]_core.py ([ESTIMATED_LINES] lines)
     - Main orchestrator class
     - All 5 frameworks integrated
     - Complete policy enforcement
     - Runtime management

  2. [framework_1]_implementation.py ([ESTIMATED_LINES] lines)
     - [FRAMEWORK_1] validator/processor
     - Schema definitions
     - Scoring logic
     - Integration hooks

  3. [framework_2]_implementation.py ([ESTIMATED_LINES] lines)
     - [FRAMEWORK_2] processor
     - Classification/evaluation logic
     - State management

  [CONTINUE FOR EACH FRAMEWORK]

  4. policy_engine.py ([ESTIMATED_LINES] lines)
     - Policy rule definitions
     - Enforcement mechanisms
     - Escalation routing
     - Audit logging

  5. integration_layer.py ([ESTIMATED_LINES] lines)
     - Integration with [EXISTING_SYSTEM_NAME]
     - Constraint application
     - Compatibility hooks

  6. config.py ([ESTIMATED_LINES] lines)
     - Configuration management
     - All parameters customizable
     - Environment-aware settings

Configuration Files:
  7. __init__.py
     - Package exports
     - Module imports

Examples & Documentation:
  8. quick_start.py
     - 6 complete working examples
     - End-to-end demonstrations
     - Integration patterns

  9. DEPLOYMENT_GUIDE.md
     - Step-by-step deployment
     - Configuration reference
     - Integration instructions
     - Troubleshooting guide

 10. PACKAGE_SUMMARY.md
     - High-level overview
     - Framework descriptions
     - Architecture diagrams
     - Performance metrics

PART 5: QUALITY REQUIREMENTS
============================

All code must:
✓ Use only Python standard library (no external dependencies)
✓ Include comprehensive type hints
✓ Have detailed docstrings on all classes/methods
✓ Implement complete error handling
✓ Include logging throughout
✓ Support full configuration
✓ Be production-ready
✓ Follow clean code principles

PART 6: DOCUMENTATION STANDARDS
==============================

Provide:
✓ Architecture diagrams (ASCII text)
✓ Data structure schemas (JSON-like format)
✓ Policy definitions (machine-readable)
✓ Configuration examples
✓ 6+ working code examples
✓ Integration guides
✓ Performance benchmarks
✓ Troubleshooting guide

PART 7: DELIVERABLES SUMMARY
=============================

Deliver:
- 10+ production-ready Python files
- 2,500+ lines of implementation code
- 1,200+ lines of documentation
- 6+ working examples
- Complete integration patterns
- Configuration templates
- Architecture documentation
- Deployment guides

OUTPUT FORMAT:
==============

Structure your response as:

1. [LAYER_NAME] OVERVIEW
   - Purpose and goals
   - Key components
   - Architecture summary

2. FRAMEWORKS INTEGRATED
   - [FRAMEWORK_1]: Purpose, classes, output
   - [FRAMEWORK_2]: Purpose, classes, output
   - [CONTINUE FOR EACH]

3. ARCHITECTURE & DESIGN
   - 4-layer architecture (with ASCII diagram)
   - Data flows (with ASCII diagram)
   - Component interactions

4. MACHINE-READABLE SCHEMAS
   - JSON-like schema definitions
   - Enum definitions
   - Data structure examples

5. POLICY DEFINITIONS
   - Policy rules (with conditions and actions)
   - Escalation logic
   - Governance thresholds

6. BENCHMARK SUITE DESIGN
   - Domain-specific benchmarks
   - Success criteria
   - Metrics definitions

7. PYTHON IMPLEMENTATION
   - Complete, working code
   - All [NUMBER_OF_FRAMEWORKS] frameworks
   - Production-ready quality
   - Ready to copy-paste and deploy

8. CONFIGURATION & INTEGRATION
   - Configuration options
   - Integration patterns
   - BSL/existing system hooks

9. QUICK START GUIDE
   - 3-step deployment
   - 5-minute setup
   - Usage examples

10. DEPLOYMENT ROADMAP
    - Phased rollout plan
    - Testing procedures
    - Success metrics

CONSTRAINTS:
============

- All code MUST be Python (standard library only)
- NO external dependencies allowed
- MUST include complete docstrings
- MUST support full configuration
- MUST include audit logging
- MUST be production-ready
- MUST include working examples
- MUST support integration with [EXISTING_SYSTEM_NAME]

RESEARCH FOCUS:
===============

Before generating code:
1. Research current best practices for [DOMAIN_TYPE] AI systems
2. Research [FRAMEWORK_1], [FRAMEWORK_2], etc. current implementations
3. Identify integration patterns with [EXISTING_SYSTEM_NAME]
4. Review governance policy trends
5. Analyze performance optimization strategies

Include citations to research where relevant.
"""

# ============================================================================
# TEMPLATE: QUICK CUSTOMIZATION GUIDE

CUSTOMIZATION_VARIABLES = {
    "[LAYER_NAME]": "Name of the layer (e.g., 'Metacognitive Reasoning Layer', 'Ethical Governance Layer')",
    "[DOMAIN_TYPE]": "Domain type (e.g., 'business decision-making and coding workflows')",
    "[NUMBER_OF_FRAMEWORKS]": "Number of frameworks (e.g., '5')",
    "[FRAMEWORK_LIST]": "List of frameworks (e.g., 'Paul-Elder, Bloom, DOK, SRL, Fink')",
    "[AGENT_TYPES]": "Types of agents (e.g., 'business analytics, coding, DevOps, model-building')",
    "[EXISTING_SYSTEM_NAME]": "System to integrate with (e.g., 'Boss Sovereignty Layer', 'L9-AI-OS')",
    "[POLICY_REQUIREMENT_1]": "First policy requirement",
    "[POLICY_REQUIREMENT_2]": "Second policy requirement",
    "[ESTIMATED_LINES]": "Estimated lines of code (e.g., '400', '500')",
}

# ============================================================================
# EXAMPLE USAGE #1: ETHICAL GOVERNANCE LAYER

EXAMPLE_ETHICAL_GOVERNANCE = """
You are an applied research team tasked with designing and implementing an
ETHICAL GOVERNANCE LAYER for an AI operating system that orchestrates business
decision-making and coding workflows. The system should integrate 5 cognitive/learning
frameworks: (1) Virtue Ethics Framework, (2) Stakeholder Impact Assessment,
(3) Transparency & Explainability Standards, (4) Value Alignment Verification,
(5) Bias Detection & Mitigation. Your goals are to:

(a) Specify how each ethical framework is represented in machine-readable form
(b) Define policies that use these representations to constrain and guide AI agents
(c) Create a production-ready Python implementation
(d) Provide comprehensive documentation and working examples

[CONTINUE WITH FULL TEMPLATE AS SPECIFIED ABOVE]
"""

# ============================================================================
# EXAMPLE USAGE #2: LEARNING & ADAPTATION LAYER

EXAMPLE_LEARNING_LAYER = """
You are an applied research team tasked with designing and implementing a
LEARNING & ADAPTATION LAYER for an AI operating system that orchestrates
technical development and model training workflows. The system should integrate
5 cognitive/learning frameworks: (1) Experiential Learning Cycle,
(2) Knowledge Organization & Retention, (3) Strategy Optimization,
(4) Skill Development Pathways, (5) Meta-Learning Assessment. Your goals are to:

(a) Specify how each learning framework is represented in machine-readable form
(b) Define policies that use these representations to constrain and guide AI agents
(c) Create a production-ready Python implementation  
(d) Provide comprehensive documentation and working examples

[CONTINUE WITH FULL TEMPLATE AS SPECIFIED ABOVE]
"""

# ============================================================================
# EXAMPLE USAGE #3: RISK MANAGEMENT LAYER

EXAMPLE_RISK_LAYER = """
You are an applied research team tasked with designing and implementing a
RISK MANAGEMENT LAYER for an AI operating system that orchestrates financial
decision-making and infrastructure management workflows. The system should integrate
5 risk management frameworks: (1) Risk Assessment & Quantification,
(2) Scenario Analysis & Stress Testing, (3) Mitigation Strategy Development,
(4) Compliance & Regulatory Requirements, (5) Risk Monitoring & Adaptation.
Your goals are to:

(a) Specify how each risk framework is represented in machine-readable form
(b) Define policies that use these representations to constrain and guide AI agents
(c) Create a production-ready Python implementation
(d) Provide comprehensive documentation and working examples

[CONTINUE WITH FULL TEMPLATE AS SPECIFIED ABOVE]
"""

# ============================================================================
# HOW TO USE WITH PERPLEXITY RESEARCH API

PERPLEXITY_API_USAGE = """
STEP 1: CUSTOMIZE THE TEMPLATE
==============================

Replace all [BRACKET_VALUES] with your specific requirements:

Example:
  [LAYER_NAME] → "Ethical Governance Layer"
  [DOMAIN_TYPE] → "financial and hiring decisions"
  [NUMBER_OF_FRAMEWORKS] → "5"
  [FRAMEWORK_LIST] → "Virtue Ethics, Stakeholder Impact, Transparency, Value Alignment, Bias Detection"
  [AGENT_TYPES] → "risk analysis, hiring, portfolio management"
  [EXISTING_SYSTEM_NAME] → "L9-AI-OS with Boss Sovereignty Layer"

STEP 2: CALL PERPLEXITY API
============================

Using Perplexity Research API:

import requests

api_key = "your-api-key"
url = "https://api.perplexity.ai/chat/completions"

prompt = SUPER_PROMPT_COGNITIVE_LAYER.replace(
    "[LAYER_NAME]", "Your Layer Name"
).replace(
    "[DOMAIN_TYPE]", "Your Domain"
)
# ... continue with all replacements

payload = {
    "model": "sonar-pro",
    "messages": [
        {
            "role": "user",
            "content": prompt
        }
    ],
    "temperature": 0.2,  # Lower for consistent code
    "top_p": 0.9,
    "return_citations": True,
    "search_domain_filter": ["perplexity.com"],
}

response = requests.post(url, json=payload, headers={
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
})

result = response.json()
print(result["choices"][0]["message"]["content"])  # noqa: ADR-0019

STEP 3: POST-PROCESS OUTPUT
===========================

The API will return structured Python code and documentation.

Format: Extract code blocks and save as separate files:

```python
# Extract code sections and save to files
# mrl_core.py
# mrl_config.py
# mrl_framework_1.py
# etc.
```

STEP 4: DEPLOY
==============

All generated files are production-ready:

cp *.py /your/deployment/path/
python quick_start.py  # Verify installation
# Ready to integrate with L9-AI-OS or your system
"""

# ============================================================================
# ADVANCED: PROMPT ENGINEERING TIPS

PROMPT_ENGINEERING_TIPS = """
TIPS FOR BEST RESULTS WITH PERPLEXITY API:

1. BE SPECIFIC ABOUT FRAMEWORKS
   - Name exact frameworks (Paul-Elder, Bloom, DOK, etc.)
   - Specify exact number of components
   - Define clear integration patterns

2. SPECIFY CODE REQUIREMENTS
   - "Production-ready Python with standard library only"
   - "Complete type hints and docstrings"
   - "Minimum 2,500 lines of code"
   - "10+ files total"

3. REQUEST SPECIFIC DELIVERABLES
   - "Include 6 working examples"
   - "Provide architecture diagrams in ASCII"
   - "Create deployment guide with 5 steps"
   - "Include performance benchmarks"

4. SET QUALITY STANDARDS
   - "No external dependencies"
   - "Comprehensive error handling"
   - "Full audit logging"
   - "Fully configurable"

5. USE RESEARCH CONTEXT
   - "Based on latest research in..."
   - "Following best practices from..."
   - "Incorporating standards from..."
   - "Validated with current benchmarks"

6. REQUEST INTEGRATION DETAILS
   - Specific integration patterns
   - Configuration examples
   - Override mechanisms
   - Compatibility hooks

7. SPECIFY OUTPUT FORMAT
   - "Structure as 10 separate Python files"
   - "Include complete docstrings"
   - "Provide inline code comments"
   - "Add architecture diagrams"

8. ASK FOR DOCUMENTATION
   - "Create 500+ line deployment guide"
   - "Include troubleshooting section"
   - "Provide quick-start examples"
   - "Add configuration reference"
"""

# ============================================================================
# TEMPLATE: MINIMAL PROMPT (For Quick Iterations)

MINIMAL_SUPER_PROMPT = """
Create a production-ready Python implementation of a [LAYER_NAME] for an AI 
operating system. Integrate these [N] frameworks: [FRAMEWORK_LIST]. 

Requirements:
- 2,500+ lines of production Python code
- Standard library only (no external dependencies)
- [N] separate modules for each framework
- 1 core orchestrator module
- 1 integration layer for [EXISTING_SYSTEM]
- 1 config module with full customization
- Complete type hints and docstrings
- Full error handling and logging
- 6+ working examples
- 500+ line deployment guide
- All files ready to copy-paste and deploy

Frameworks to integrate:
1. [FRAMEWORK_1]: Purpose, classes, output format
2. [FRAMEWORK_2]: Purpose, classes, output format
[CONTINUE...]

Deliver:
- Complete Python implementation
- Architecture diagrams (ASCII)
- Schema definitions
- Policy rules
- Quick-start guide
- Deployment instructions
- Integration patterns
"""

# ============================================================================
# TEMPLATE: EXTENDED PROMPT (For Comprehensive Results)

EXTENDED_SUPER_PROMPT = """
You are tasked with designing and implementing [LAYER_NAME], a comprehensive
cognitive governance layer for [AI_SYSTEM_NAME]. This system orchestrates
[WORKFLOW_TYPES] and must integrate [N] research-backed frameworks.

CONTEXT:
========
Current System: [EXISTING_SYSTEM_NAME]
Integration Points: [INTEGRATION_POINTS]
Deployment Target: [DEPLOYMENT_ENV]
Scale Requirements: [SCALE_REQUIREMENTS]
Performance Requirements: [PERF_REQUIREMENTS]

FRAMEWORKS TO INTEGRATE:
=======================
[FRAMEWORK_1]:
  - Core concepts and components
  - How to represent in code
  - Validation criteria
  - Scoring/evaluation logic
  - Integration with other frameworks

[CONTINUE FOR EACH FRAMEWORK]

DELIVERABLES REQUIRED:
======================
1. Architecture Design
   - 4-layer architecture diagram
   - Component descriptions
   - Data flow diagrams
   - Integration points

2. Python Implementation (2,500+ lines)
   - [N] Framework modules
   - Core orchestrator
   - Policy engine
   - Integration layer
   - Configuration management
   - Runtime executor
   - Audit logging
   - Metrics collection

3. Documentation (1,200+ lines)
   - Deployment guide (500+ lines)
   - Package summary
   - File index
   - Troubleshooting guide
   - Performance benchmarks

4. Examples & Quick Start
   - 6 complete working examples
   - Quick-start guide (3-step deployment)
   - Integration patterns
   - Configuration templates

5. Testing & Validation
   - Test cases (included in code)
   - Example scenarios
   - Verification procedures
   - Performance benchmarks

QUALITY STANDARDS:
==================
✓ Production-ready code
✓ Zero external dependencies
✓ Comprehensive type hints
✓ Full docstrings (minimum 50 lines per class)
✓ Complete error handling
✓ Audit logging throughout
✓ Full configuration support
✓ Clean architecture
✓ Security reviewed
✓ Performance optimized

OUTPUT FORMAT:
==============
1. Executive Summary
2. Framework Descriptions
3. Architecture & Design
4. Machine-Readable Schemas
5. Complete Python Implementation
6. Configuration & Integration
7. Documentation & Guides
8. Deployment Instructions
9. Quick-Start Examples
10. Support & Troubleshooting

RESEARCH TO INCLUDE:
====================
- Latest research on [FRAMEWORKS]
- Current best practices in [DOMAIN]
- Relevant standards and benchmarks
- Performance optimization strategies
- Security considerations
- Integration patterns

Include citations where relevant.
"""

# ============================================================================
# HELPER: FRAMEWORK DESCRIPTION TEMPLATE

FRAMEWORK_DESCRIPTION_TEMPLATE = """
[FRAMEWORK_NAME]

Purpose:
  [What this framework does and why it matters]

Core Components:
  • Component 1: [Description]
  • Component 2: [Description]
  • Component 3: [Description]

Data Structures:
  - Enum/Class definitions
  - Validation schemas
  - Output formats

Integration Points:
  - How it connects to other frameworks
  - Dependencies and triggers
  - Constraint application

Machine-Readable Representation:
  [JSON/Python dict example]

Scoring & Evaluation:
  - Metrics and thresholds
  - Calculation methods
  - Output ranges

Example Use Case:
  [Concrete example of framework in action]

Governance Rules:
  - When to apply this framework
  - What actions to take
  - Escalation criteria
"""

# ============================================================================
# SUMMARY & QUICK REFERENCE

QUICK_REFERENCE = """
SUPER PROMPT QUICK REFERENCE
============================

For complete AI OS layer generation with Perplexity Research API:

1. USE TEMPLATE: SUPER_PROMPT_COGNITIVE_LAYER
2. CUSTOMIZE: Replace all [BRACKET_VALUES]
3. API CALL: Send to Perplexity Research API (model: sonar-pro)
4. EXTRACT: Copy Python code blocks to files
5. DEPLOY: Ready for immediate use

Expected Results:
  - 10+ Python files (2,500+ lines)
  - Complete documentation (1,200+ lines)
  - 6+ working examples
  - Production-ready code
  - Zero setup required

Time to Deploy: 50 minutes

Key Features:
  ✓ 5 integrated cognitive frameworks
  ✓ Machine-readable policies
  ✓ Complete governance enforcement
  ✓ BSL/existing system integration
  ✓ Audit logging & metrics
  ✓ Full configuration support
  ✓ Production-ready quality

Files Generated:
  - Framework implementation modules
  - Core orchestrator
  - Policy engine
  - Integration layer
  - Configuration management
  - Runtime executor
  - Package initialization
  - Quick-start examples
  - Deployment guide
  - Support documentation
"""

# ============================================================================
# END OF TEMPLATE

if __name__ == "__main__":
    print("SUPER PROMPT TEMPLATE FOR AI OS LAYER GENERATION")  # noqa: ADR-0019
    print("=" * 70)  # noqa: ADR-0019
    print("\nUSAGE:")  # noqa: ADR-0019
    print("1. Import this template")  # noqa: ADR-0019
    print("2. Customize SUPER_PROMPT_COGNITIVE_LAYER with your values")  # noqa: ADR-0019
    print("3. Send to Perplexity Research API")  # noqa: ADR-0019
    print("4. Extract and save generated Python files")  # noqa: ADR-0019
    print("5. Deploy immediately")  # noqa: ADR-0019
    print("\nExamples provided for:")  # noqa: ADR-0019
    print("- Ethical Governance Layer")  # noqa: ADR-0019
    print("- Learning & Adaptation Layer")  # noqa: ADR-0019
    print("- Risk Management Layer")  # noqa: ADR-0019
    print("\nFor more customization options, see PROMPT_ENGINEERING_TIPS")  # noqa: ADR-0019
    print("\nTotal lines of code generation possible: 2,500+ per API call")  # noqa: ADR-0019
    print("Total documentation generation possible: 1,200+ lines per API call")  # noqa: ADR-0019

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
        "foundation",
        "messaging",
        "metrics",
        "monitoring",
        "performance",
        "testing",
    ],
    "keywords": ["prompt", "super", "template"],
    "business_value": "Complete Python script packets (2,500+ lines) Multi-file modular architectures Production-ready implementations Comprehensive documentation Working examples and quick-start guides Integration patterns",
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
