import pytest


def test_sanitizer_rejects_non_object_arguments():
    from core.tools.sanitizer import ToolInputSanitizationError, ToolInputSanitizer

    s = ToolInputSanitizer()
    with pytest.raises(ToolInputSanitizationError):
        s.sanitize(
            tool_id="t", arguments=["not", "a", "dict"], schema={"type": "object"}
        )


def test_sanitizer_enforces_required_fields():
    from core.tools.sanitizer import ToolInputSanitizationError, ToolInputSanitizer

    s = ToolInputSanitizer()
    schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }
    with pytest.raises(ToolInputSanitizationError) as exc:
        s.sanitize(tool_id="t", arguments={}, schema=schema)
    assert "missing required fields" in str(exc.value)


def test_sanitizer_rejects_unknown_keys_when_schema_has_properties():
    from core.tools.sanitizer import ToolInputSanitizationError, ToolInputSanitizer

    s = ToolInputSanitizer()
    schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }
    with pytest.raises(ToolInputSanitizationError) as exc:
        s.sanitize(tool_id="t", arguments={"query": "x", "oops": 1}, schema=schema)
    assert "unknown field" in str(exc.value)


def test_sanitizer_coerces_int_and_strips_strings():
    from core.tools.sanitizer import ToolInputSanitizer

    s = ToolInputSanitizer()
    schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer"},
            "query": {"type": "string"},
        },
        "required": ["query"],
    }
    out = s.sanitize(
        tool_id="t", arguments={"query": "  hi ", "limit": "7"}, schema=schema
    )
    assert out["query"] == "hi"
    assert out["limit"] == 7


def test_sanitizer_blocks_path_traversal_for_path_like_keys():
    from core.tools.sanitizer import ToolInputSanitizationError, ToolInputSanitizer

    s = ToolInputSanitizer()
    schema = {
        "type": "object",
        "properties": {"file_path": {"type": "string"}},
        "required": [],
    }
    with pytest.raises(ToolInputSanitizationError):
        s.sanitize(
            tool_id="t", arguments={"file_path": "../secrets.env"}, schema=schema
        )
