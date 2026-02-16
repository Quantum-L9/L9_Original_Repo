"""
Comprehensive Test Suite for SpecNormalizer v2.0.0

Tests:
- YAML/JSON/dict parsing
- Field validation and normalization
- Default value filling
- Module ID generation
- Error handling (parse vs validation errors)
- Frozen immutability of NormalizedSpec
- Round-trip serialization
"""

import json
import tempfile
from pathlib import Path

import pytest

from core.codegen.spec import (
    NormalizedSpec,
    SpecNormalizer,
    SpecParseError,
    SpecValidationError,
)
from core.decorators import must_stay_async

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def normalizer():
    """Create SpecNormalizer instance"""
    return SpecNormalizer()


@pytest.fixture
def valid_spec_dict():
    """Valid minimal Module-Spec v2.6"""
    return {
        "metadata": {
            "name": "My Test Agent",
            "description": "This is a test agent for unit testing purposes.",
            "version": "1.0.0",
        },
        "governance": {
            "tier": 2,
            "escalation_path": "Igor",
        },
        "system": {
            "role": "General Agent",
            "capabilities": ["reasoning", "planning"],
            "constraints": ["no_external_api"],
        },
        "integration": {
            "depends_on": ["memory.service", "tool_registry"],
            "provides": ["inference"],
            "memory_access": True,
            "tool_registry": True,
        },
        "dependency_contract": {
            "external_services": [{"name": "openai", "version": "1.0.0"}],
            "kernel_requirements": ["01-master-kernel.yaml"],
            "memory_substrates": ["PostgreSQL", "Redis"],
        },
    }


@pytest.fixture
def minimal_spec_dict():
    """Minimal valid spec (only required fields)"""
    return {
        "metadata": {
            "name": "Simple Agent",
            "description": "A simple test agent with minimal configuration.",
        }
    }


# =============================================================================
# TEST: YAML PARSING
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_parse_valid_yaml(normalizer, valid_spec_dict):
    """Test parsing valid YAML spec"""
    yaml_content = """
metadata:
  name: My Test Agent
  description: This is a test agent for unit testing purposes.
  version: 1.0.0
governance:
  tier: 2
  escalation_path: Igor
system:
  role: General Agent
  capabilities:
    - reasoning
    - planning
  constraints:
    - no_external_api
integration:
  depends_on:
    - memory.service
    - tool_registry
  provides:
    - inference
  memory_access: true
  tool_registry: true
dependency_contract:
  external_services:
    - name: openai
      version: 1.0.0
  kernel_requirements:
    - 01-master-kernel.yaml
  memory_substrates:
    - PostgreSQL
    - Redis
"""

    result = await normalizer.normalize_from_yaml(yaml_content)

    assert isinstance(result, NormalizedSpec)
    assert result.module_name == "My Test Agent"
    assert result.tier == 2
    assert "reasoning" in result.capabilities
    assert result.normalized_from == "yaml"


@pytest.mark.asyncio
async def test_parse_invalid_yaml(normalizer):
    """Test parsing invalid YAML raises SpecParseError"""
    invalid_yaml = """
invalid:
  yaml: [
  unclosed bracket
"""

    with pytest.raises(SpecParseError, match="Invalid YAML"):
        await normalizer.normalize_from_yaml(invalid_yaml)


@pytest.mark.asyncio
async def test_parse_yaml_non_dict(normalizer):
    """Test YAML that parses to non-dict raises SpecParseError"""
    yaml_content = """- item1
- item2
"""

    with pytest.raises(SpecParseError, match="must parse to a dictionary"):
        await normalizer.normalize_from_yaml(yaml_content)


# =============================================================================
# TEST: JSON PARSING
# =============================================================================


@pytest.mark.asyncio
async def test_parse_valid_json(normalizer, valid_spec_dict):
    """Test parsing valid JSON spec"""
    json_content = json.dumps(valid_spec_dict)

    result = await normalizer.normalize_from_json(json_content)

    assert isinstance(result, NormalizedSpec)
    assert result.module_name == "My Test Agent"
    assert result.tier == 2
    assert result.normalized_from == "json"


@pytest.mark.asyncio
async def test_parse_invalid_json(normalizer):
    """Test parsing invalid JSON raises SpecParseError"""
    invalid_json = "{invalid json}"

    with pytest.raises(SpecParseError, match="Invalid JSON"):
        await normalizer.normalize_from_json(invalid_json)


@pytest.mark.asyncio
async def test_parse_json_non_dict(normalizer):
    """Test JSON that parses to non-dict raises SpecParseError"""
    json_content = json.dumps(["item1", "item2"])

    with pytest.raises(SpecParseError, match="must parse to an object"):
        await normalizer.normalize_from_json(json_content)


# =============================================================================
# TEST: DICT PARSING (MAIN LOGIC)
# =============================================================================


@pytest.mark.asyncio
async def test_normalize_valid_dict(normalizer, valid_spec_dict):
    """Test normalization of valid dict"""
    result = await normalizer.normalize_from_dict(valid_spec_dict)

    assert isinstance(result, NormalizedSpec)
    assert result.module_name == "My Test Agent"
    assert (
        result.module_description == "This is a test agent for unit testing purposes."
    )
    assert result.module_version == "1.0.0"
    assert result.tier == 2
    assert result.escalation_path == "Igor"
    assert "reasoning" in result.capabilities
    assert "memory.service" in result.depends_on
    assert result.memory_access is True
    assert result.tool_registry is True


@pytest.mark.asyncio
async def test_normalize_minimal_dict(normalizer, minimal_spec_dict):
    """Test normalization with defaults for optional fields"""
    result = await normalizer.normalize_from_dict(minimal_spec_dict)

    assert isinstance(result, NormalizedSpec)
    # Required fields
    assert result.module_name == "Simple Agent"
    assert (
        result.module_description == "A simple test agent with minimal configuration."
    )
    # Defaults
    assert result.module_version == "1.0.0"
    assert result.tier == 2
    assert result.escalation_path == "Igor"
    assert result.module_domain == "general"
    assert result.module_role == "General Agent"
    assert result.requires_approval is False
    assert result.risk_level == "low"
    assert len(result.capabilities) == 0  # Empty tuple
    assert result.memory_access is False
    assert result.tool_registry is False


@pytest.mark.asyncio
async def test_normalize_missing_required_field(normalizer):
    """Test that missing required fields raise SpecValidationError"""
    spec = {
        "metadata": {
            "name": "Test",
            # Missing required 'description' field
        }
    }

    with pytest.raises(SpecValidationError, match="Invalid spec"):
        await normalizer.normalize_from_dict(spec)


@pytest.mark.asyncio
async def test_normalize_invalid_field_type(normalizer):
    """Test that invalid field types raise SpecValidationError"""
    spec = {
        "metadata": {
            "name": "Test",
            "description": "Test description",
        },
        "governance": {
            "tier": "invalid_tier",  # Should be int
        },
    }

    with pytest.raises(SpecValidationError, match="Invalid spec"):
        await normalizer.normalize_from_dict(spec)


# =============================================================================
# TEST: MODULE ID GENERATION
# =============================================================================


def test_generate_module_id_from_name(normalizer):
    """Test module ID generation from name"""
    # Simple case
    assert normalizer._generate_module_id("My Test Agent") == "my_test_agent"

    # With special characters
    assert normalizer._generate_module_id("My-Test Agent!") == "my_test_agent"

    # With multiple spaces/underscores
    assert normalizer._generate_module_id("My  __  Test") == "my_test"

    # Leading/trailing special chars
    assert normalizer._generate_module_id("---Test Agent---") == "test_agent"


def test_generate_module_id_override(normalizer):
    """Test module ID explicit override"""
    override_id = "custom_module_id"
    result = normalizer._generate_module_id("My Test", override=override_id)
    assert result == override_id


def test_generate_module_id_empty_string(normalizer):
    """Test module ID generation from empty string"""
    result = normalizer._generate_module_id("")
    # Should generate random ID
    assert result.startswith("module_")
    assert len(result) > len("module_")


# =============================================================================
# TEST: NAME NORMALIZATION
# =============================================================================


def test_normalize_name(normalizer):
    """Test display name normalization"""
    # All lowercase
    assert normalizer._normalize_name("my test agent") == "My Test Agent"

    # All uppercase
    assert normalizer._normalize_name("MY TEST AGENT") == "My Test Agent"

    # Mixed case
    assert normalizer._normalize_name("My teSt aGeNt") == "My Test Agent"

    # Already normalized
    assert normalizer._normalize_name("My Test Agent") == "My Test Agent"


# =============================================================================
# TEST: FILE OPERATIONS
# =============================================================================


@pytest.mark.asyncio
async def test_normalize_from_yaml_file(normalizer, valid_spec_dict):
    """Test loading and normalizing YAML file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create YAML file
        spec_file = Path(tmpdir) / "spec.yaml"
        yaml_content = """
metadata:
  name: File Test Agent
  description: Test agent loaded from file.
  version: 2.0.0
"""
        spec_file.write_text(yaml_content)

        # Normalize from file
        result = await normalizer.normalize_from_file(spec_file)

        assert isinstance(result, NormalizedSpec)
        assert result.module_name == "File Test Agent"
        assert result.module_version == "2.0.0"


@pytest.mark.asyncio
async def test_normalize_from_json_file(normalizer, minimal_spec_dict):
    """Test loading and normalizing JSON file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create JSON file
        spec_file = Path(tmpdir) / "spec.json"
        spec_file.write_text(json.dumps(minimal_spec_dict))

        # Normalize from file
        result = await normalizer.normalize_from_file(spec_file)

        assert isinstance(result, NormalizedSpec)
        assert result.module_name == "Simple Agent"


@pytest.mark.asyncio
async def test_normalize_from_missing_file(normalizer):
    """Test that missing file raises SpecParseError"""
    missing_file = Path("/nonexistent/spec.yaml")

    with pytest.raises(SpecParseError, match="Spec file not found"):
        await normalizer.normalize_from_file(missing_file)


@pytest.mark.asyncio
async def test_normalize_from_unsupported_format(normalizer):
    """Test that unsupported file format raises SpecParseError"""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_file = Path(tmpdir) / "spec.txt"
        spec_file.write_text("invalid format")

        with pytest.raises(SpecParseError, match="Unsupported file format"):
            await normalizer.normalize_from_file(spec_file)


# =============================================================================
# TEST: NORMALIZED SPEC IMMUTABILITY
# =============================================================================


@pytest.mark.asyncio
async def test_normalized_spec_is_frozen(normalizer, minimal_spec_dict):
    """Test that NormalizedSpec is frozen (immutable after creation)"""
    result = await normalizer.normalize_from_dict(minimal_spec_dict)

    # Should raise FrozenInstanceError when attempting to modify
    with pytest.raises((AttributeError, Exception)):
        result.tier = 4  # type: ignore

    with pytest.raises((AttributeError, Exception)):
        result.module_name = "Modified"  # type: ignore


# =============================================================================
# TEST: SERIALIZATION
# =============================================================================


@pytest.mark.asyncio
async def test_normalized_spec_to_dict(normalizer, valid_spec_dict):
    """Test serialization to dict"""
    result = await normalizer.normalize_from_dict(valid_spec_dict)
    result_dict = result.to_dict()

    assert isinstance(result_dict, dict)
    assert result_dict["module_name"] == "My Test Agent"
    assert result_dict["tier"] == 2
    assert isinstance(result_dict["capabilities"], tuple)


@pytest.mark.asyncio
async def test_normalized_spec_to_json(normalizer, valid_spec_dict):
    """Test serialization to JSON"""
    result = await normalizer.normalize_from_dict(valid_spec_dict)
    json_str = result.to_json()

    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert parsed["module_name"] == "My Test Agent"
    assert parsed["tier"] == 2


# =============================================================================
# TEST: ROUND-TRIP OPERATIONS
# =============================================================================


@pytest.mark.asyncio
async def test_roundtrip_parse_serialize(normalizer, valid_spec_dict):
    """Test round-trip: dict -> normalize -> to_dict"""
    # Normalize
    normalized = await normalizer.normalize_from_dict(valid_spec_dict)
    # Serialize
    output_dict = normalized.to_dict()

    assert output_dict["module_name"] == "My Test Agent"
    assert output_dict["tier"] == 2
    assert output_dict["memory_access"] is True


# =============================================================================
# TEST: INTEGRATION WITH COMPILER
# =============================================================================


@pytest.mark.asyncio
async def test_normalizer_with_compiler_flow(normalizer, valid_spec_dict):
    """Test normalizer in realistic compiler flow"""
    # Simulate compiler receiving raw spec
    raw_spec = valid_spec_dict

    # Normalizer parses it
    normalized = await normalizer.normalize_from_dict(raw_spec)

    # Compiler should work with NormalizedSpec
    assert hasattr(normalized, "module_id")
    assert hasattr(normalized, "module_name")
    assert hasattr(normalized, "tier")
    assert hasattr(normalized, "to_dict")

    # Convert to dict for template rendering
    spec_dict = normalized.to_dict()
    assert isinstance(spec_dict, dict)
    assert spec_dict["module_id"]  # Has generated module_id


# =============================================================================
# TEST: ERROR SCENARIOS
# =============================================================================


@pytest.mark.asyncio
async def test_error_handling_parse_error_message(normalizer):
    """Test that SpecParseError has clear message"""
    try:
        await normalizer.normalize_from_yaml("invalid: yaml: {")
    except SpecParseError as e:
        assert "Invalid YAML" in str(e)


@pytest.mark.asyncio
async def test_error_handling_validation_error_message(normalizer):
    """Test that SpecValidationError has clear message"""
    spec = {
        "metadata": {
            "name": "Test",
            # Missing description
        }
    }
    try:
        await normalizer.normalize_from_dict(spec)
    except SpecValidationError as e:
        assert "Invalid spec" in str(e)


# =============================================================================
# PERFORMANCE TEST
# =============================================================================


@pytest.mark.asyncio
async def test_normalize_performance(normalizer):
    """Test normalization performance (should be fast)"""
    import time

    spec_dict = {
        "metadata": {
            "name": "Performance Test Agent",
            "description": "Testing normalization speed.",
        }
    }

    start = time.time()
    for _ in range(100):
        await normalizer.normalize_from_dict(spec_dict)
    elapsed = time.time() - start

    # 100 normalizations should take < 1 second
    assert elapsed < 1.0, f"Normalization too slow: {elapsed}s for 100 iterations"
