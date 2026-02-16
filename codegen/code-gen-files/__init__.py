"""
L9 Research Factory - Schema-Driven Code Generation
====================================================

The Research Factory transforms YAML agent schemas into production-ready code.

Core Principle: Schema → Parse → Validate → Extract → Deploy

Components:
- schema_parser: Parse YAML schemas into validated Pydantic models
- schema_validator: Validate schemas against Research Factory rules
- glue_resolver: Resolve inter-agent dependencies
- extractor: Generate code from schemas using templates
- migrations: Schema versioning and migration support

Usage:
    from services.research_factory import (
        parse_schema,
        validate_schema,
        UniversalExtractor,
    )

    # Parse schema
    schema = parse_schema("path/to/schema.yaml")

    # Validate
    result = validate_schema(schema)
    if result.valid:
        # Extract
        extractor = UniversalExtractor()
        result = await extractor.extract(schema, "output/dir")

Version: 1.0.0
"""

from services.research_factory.extractor import (
    ExtractionManifest,
    ExtractionResult,
    GeneratedFile,
    UniversalExtractor,
    create_extractor,
    extract_agent,
)
from services.research_factory.glue_resolver import (
    DependencyGraph,
    GlueConfig,
    GlueResolver,
    ImportSpec,
    WiringSpec,
    create_empty_glue_config,
    load_glue_config,
)
from services.research_factory.schema_parser import (
    AgentSchema,
    CollaborationNetworkBlock,
    CommunicationStackBlock,
    CursorInstructionsBlock,
    DeploymentBlock,
    GovernanceBlock,
    IntegrationBlock,
    LearningSystemBlock,
    MemoryTopologyBlock,
    MetadataBlock,
    ReasoningEngineBlock,
    SystemBlock,
    WorldModelIntegrationBlock,
    parse_schema,
)
from services.research_factory.schema_validator import (
    SchemaValidator,
    ValidationError,
    ValidationResult,
    validate_schema,
    validate_schema_file,
    validate_schema_yaml,
)

__all__ = [
    # Core schema model
    "AgentSchema",
    # Block models
    "SystemBlock",
    "IntegrationBlock",
    "GovernanceBlock",
    "MemoryTopologyBlock",
    "CommunicationStackBlock",
    "ReasoningEngineBlock",
    "CollaborationNetworkBlock",
    "LearningSystemBlock",
    "WorldModelIntegrationBlock",
    "CursorInstructionsBlock",
    "DeploymentBlock",
    "MetadataBlock",
    # Parser functions
    "parse_schema",
    # Validator
    "SchemaValidator",
    "ValidationResult",
    "ValidationError",
    "validate_schema",
    "validate_schema_file",
    "validate_schema_yaml",
    # Glue resolver
    "GlueResolver",
    "GlueConfig",
    "WiringSpec",
    "ImportSpec",
    "DependencyGraph",
    "load_glue_config",
    "create_empty_glue_config",
    # Extractor
    "UniversalExtractor",
    "ExtractionResult",
    "ExtractionManifest",
    "GeneratedFile",
    "extract_agent",
    "create_extractor",
]
