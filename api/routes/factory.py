# ============================================================================
__dora_meta__ = {
    "component_name": "Factory",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "factory",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "GET /health",
            "POST /validate",
            "POST /extract",
            "POST /extract-file",
            "GET /templates",
            "GET /templates/{template_name}",
        ],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["api.server", "tests.api.test_factory_path_safety"],
    },
}
# ============================================================================

# CodeGen????

"""
L9 Research Factory API Routes
==============================

REST API endpoints for the Research Factory:
- POST /factory/extract - Extract agent from schema
- POST /factory/validate - Validate schema without extracting
- GET /factory/templates - List available templates
- GET /factory/health - Health check

Version: 1.0.0
"""

from __future__ import annotations

import structlog
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/factory", tags=["research-factory"])

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="",  # Router already has prefix="/factory"
    tags=["research-factory"],
    module_id="factory",
    display_name="Research Factory",
)


# =============================================================================
# Request/Response Models
# =============================================================================


class ValidateRequest(BaseModel):
    """Request model for schema validation."""

    schema_yaml: str = Field(..., description="YAML schema content")
    strict: bool = Field(default=False, description="Enable strict validation")

    model_config = {"extra": "forbid"}


class ValidateResponse(BaseModel):
    """Response model for schema validation."""

    valid: bool = Field(..., description="Whether schema is valid")
    error_count: int = Field(default=0, description="Number of errors")
    warning_count: int = Field(default=0, description="Number of warnings")
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    agent_id: Optional[str] = Field(None, description="Parsed agent ID if valid")

    model_config = {"extra": "forbid"}


class ExtractRequest(BaseModel):
    """Request model for agent extraction."""

    schema_yaml: str = Field(..., description="YAML schema content")
    output_dir: str = Field(
        ..., description="Output directory (relative to sandbox root)"
    )
    glue_yaml: Optional[str] = Field(
        None, description="Optional glue configuration YAML"
    )
    overwrite: bool = Field(default=False, description="Overwrite existing files")
    dry_run: bool = Field(default=False, description="Validate only, don't write files")
    strict: bool = Field(default=False, description="Enable strict validation")

    model_config = {"extra": "forbid"}


class ExtractResponse(BaseModel):
    """Response model for agent extraction."""

    success: bool = Field(..., description="Whether extraction succeeded")
    agent_id: Optional[str] = Field(None, description="Extracted agent ID")
    file_count: int = Field(default=0, description="Number of files generated")
    files: list[str] = Field(default_factory=list, description="Generated file paths")
    error_count: int = Field(default=0, description="Number of errors")
    warning_count: int = Field(default=0, description="Number of warnings")
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int = Field(
        default=0, description="Extraction duration in milliseconds"
    )
    manifest: Optional[dict[str, Any]] = Field(None, description="Extraction manifest")

    model_config = {"extra": "forbid"}


class TemplateInfo(BaseModel):
    """Information about a template."""

    name: str
    description: str

    model_config = {"extra": "forbid"}


class TemplatesResponse(BaseModel):
    """Response model for template listing."""

    templates: list[TemplateInfo] = Field(default_factory=list)
    count: int = Field(default=0)

    model_config = {"extra": "forbid"}


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Health status")
    service: str = Field(default="research-factory")
    templates_available: int = Field(default=0)

    model_config = {"extra": "forbid"}


class PathSafetyConfig(BaseModel):
    """Configured output root for extraction endpoints."""

    base_dir: str = Field(..., description="Base directory for extraction outputs")

    model_config = {"extra": "forbid"}


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/health", response_model=HealthResponse)
@must_stay_async("FastAPI/ASGI route handler")
async def factory_health() -> HealthResponse:
    """
    Health check for the Research Factory.

    Returns:
        HealthResponse with status
    """
    try:
        from services.research_factory.extractor import UniversalExtractor

        extractor = UniversalExtractor()
        templates = extractor.list_templates()

        return HealthResponse(
            status="healthy",
            service="research-factory",
            templates_available=len(templates),
        )
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return HealthResponse(
            status="unhealthy",
            service="research-factory",
            templates_available=0,
        )


def _safe_output_dir(output_dir: str) -> str:
    from core.security.path_safety import (
        PathSafetyError,
        resolve_base_dir,
        safe_resolve_path,
    )

    base_root = resolve_base_dir()
    try:
        safe_path = safe_resolve_path(base_root, output_dir)
    except PathSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return str(safe_path)


@router.post("/validate", response_model=ValidateResponse)
@must_stay_async("FastAPI/ASGI route handler")
async def validate_schema(body: ValidateRequest) -> ValidateResponse:
    """
    Validate a schema without extracting.

    Args:
        body: ValidateRequest with schema YAML

    Returns:
        ValidateResponse with validation results
    """
    try:
        from services.research_factory.schema_parser import parse_schema
        from services.research_factory.schema_validator import SchemaValidator

        # Parse schema
        try:
            schema = parse_schema(body.schema_yaml)
        except Exception as e:
            return ValidateResponse(
                valid=False,
                error_count=1,
                errors=[{"code": "PARSE_ERROR", "message": str(e)}],
            )

        # Validate
        validator = SchemaValidator(strict=body.strict)
        result = validator.validate(schema)

        return ValidateResponse(
            valid=result.valid,
            error_count=result.error_count,
            warning_count=result.warning_count,
            errors=[
                {"code": e.code, "message": e.message, "path": e.path}
                for e in result.errors
            ],
            warnings=[
                {"code": w.code, "message": w.message, "path": w.path}
                for w in result.warnings
            ],
            agent_id=schema.get_agent_id() if result.valid else None,
        )

    except Exception as e:
        logger.exception("Validation failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")


@router.post("/extract", response_model=ExtractResponse)
async def extract_agent(body: ExtractRequest) -> ExtractResponse:
    """
    Extract agent code from a schema.

    Args:
        body: ExtractRequest with schema YAML and options

    Returns:
        ExtractResponse with extraction results (output_dir is sandboxed)
    """
    try:
        from services.research_factory.extractor import UniversalExtractor
        from services.research_factory.glue_resolver import GlueConfig

        # Create extractor
        extractor = UniversalExtractor(strict_validation=body.strict)

        # Parse glue config if provided
        glue = None
        if body.glue_yaml:
            import yaml

            glue_data = yaml.safe_load(body.glue_yaml)
            glue = GlueConfig.model_validate(glue_data or {})

        # Extract
        result = await extractor.extract(
            schema=body.schema_yaml,
            output_dir=_safe_output_dir(body.output_dir),
            glue=glue,
            overwrite=body.overwrite,
            dry_run=body.dry_run,
        )

        return ExtractResponse(
            success=result.success,
            agent_id=result.schema.get_agent_id() if result.schema else None,
            file_count=len(result.generated_files),
            files=[str(f.path) for f in result.generated_files],
            error_count=len(result.errors),
            warning_count=len(result.warnings),
            errors=result.errors,
            warnings=result.warnings,
            duration_ms=result.duration_ms,
            manifest=result.manifest.to_dict() if result.manifest else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Extraction failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


@router.post("/extract-file", response_model=ExtractResponse)
async def extract_agent_file(
    schema_file: UploadFile = File(..., description="YAML schema file"),
    output_dir: str = Form(
        ..., description="Output directory (relative to sandbox root)"
    ),
    glue_file: Optional[UploadFile] = File(
        None, description="Optional glue config file"
    ),
    overwrite: bool = Form(False, description="Overwrite existing files"),
    dry_run: bool = Form(False, description="Validate only, don't write"),
    strict: bool = Form(False, description="Strict validation"),
) -> ExtractResponse:
    """
    Extract agent from uploaded schema file.

    Args:
        schema_file: Uploaded YAML schema file
        output_dir: Output directory path (relative to sandbox root)
        glue_file: Optional uploaded glue configuration file
        overwrite: Overwrite existing files
        dry_run: Validate only mode
        strict: Strict validation mode

    Returns:
        ExtractResponse with extraction results
    """
    try:
        from services.research_factory.extractor import UniversalExtractor
        from services.research_factory.glue_resolver import GlueConfig
        import yaml

        # Read schema file
        schema_content = await schema_file.read()
        schema_yaml = schema_content.decode("utf-8")

        # Read glue file if provided
        glue = None
        if glue_file:
            glue_content = await glue_file.read()
            glue_yaml = glue_content.decode("utf-8")
            glue_data = yaml.safe_load(glue_yaml)
            glue = GlueConfig.model_validate(glue_data or {})

        # Create extractor
        extractor = UniversalExtractor(strict_validation=strict)

        # Extract
        result = await extractor.extract(
            schema=schema_yaml,
            output_dir=_safe_output_dir(output_dir),
            glue=glue,
            overwrite=overwrite,
            dry_run=dry_run,
        )

        return ExtractResponse(
            success=result.success,
            agent_id=result.schema.get_agent_id() if result.schema else None,
            file_count=len(result.generated_files),
            files=[str(f.path) for f in result.generated_files],
            error_count=len(result.errors),
            warning_count=len(result.warnings),
            errors=result.errors,
            warnings=result.warnings,
            duration_ms=result.duration_ms,
            manifest=result.manifest.to_dict() if result.manifest else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("File extraction failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


@router.get("/templates", response_model=TemplatesResponse)
@must_stay_async("FastAPI/ASGI route handler")
async def list_templates() -> TemplatesResponse:
    """
    List available extraction templates.

    Returns:
        TemplatesResponse with template info
    """
    try:
        from services.research_factory.extractor import UniversalExtractor

        extractor = UniversalExtractor()
        template_names = extractor.list_templates()

        # Template descriptions
        descriptions = {
            "controller.py.j2": "Agent controller with lifecycle management",
            "__init__.py.j2": "Module initialization file",
            "test_agent.py.j2": "Pytest test suite for the agent",
            "README.md.j2": "Agent documentation",
        }

        templates = [
            TemplateInfo(
                name=name,
                description=descriptions.get(name, "Custom template"),
            )
            for name in template_names
        ]

        return TemplatesResponse(
            templates=templates,
            count=len(templates),
        )

    except Exception as e:
        logger.exception("Failed to list templates: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {e}")


@router.get("/templates/{template_name}")
@must_stay_async("FastAPI/ASGI route handler")
async def get_template(template_name: str) -> dict[str, Any]:
    """
    Get content of a specific template.

    Args:
        template_name: Name of the template

    Returns:
        Template content
    """
    try:
        from services.research_factory.extractor import UniversalExtractor

        extractor = UniversalExtractor()
        content = extractor.get_template_content(template_name)

        if content is None:
            raise HTTPException(
                status_code=404, detail=f"Template not found: {template_name}"
            )

        return {
            "name": template_name,
            "content": content,
            "lines": content.count("\n") + 1,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get template: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get template: {e}")


# =============================================================================
# Startup/Shutdown
# =============================================================================


@must_stay_async("health endpoint")
async def startup():
    """Called on app startup."""
    logger.info("Research Factory routes initialized")


@must_stay_async("health endpoint")
async def shutdown():
    """Called on app shutdown."""
    logger.info("Research Factory routes shutting down")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-021",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "core.security.path_safety"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "config",
        "endpoint",
        "logging",
        "messaging",
        "operations",
        "pydantic",
        "rest-api",
    ],
    "keywords": [
        "agent",
        "extract",
        "factory",
        "health",
        "safety",
        "schema",
        "shutdown",
        "startup",
    ],
    "business_value": "POST /factory/extract - Extract agent from schema POST /factory/validate - Validate schema without extracting GET /factory/templates - List available templates GET /factory/health - Health check Versi",
    "last_modified": "2026-01-17T23:47:56Z",
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
