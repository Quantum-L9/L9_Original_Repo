"""
Tests for Cypher Template Library (GMP-55)

Tests parameterized Cypher templates that prevent LLM hallucination.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from memory.cypher_templates import (
    CYPHER_TEMPLATES,
    CypherTemplate,
    CypherTemplateCategory,
    CypherTemplateLibrary,
    execute_template,
    get_template_library,
)


class TestCypherTemplateLibrary:
    """Test CypherTemplateLibrary functionality."""

    def test_library_initialization(self):
        """Test library initializes with default templates."""
        library = CypherTemplateLibrary()

        # Should have default templates
        templates = library.list_templates()
        assert len(templates) > 0

        # Check for key templates
        template_names = {t["name"] for t in templates}
        assert "find_shortest_path" in template_names
        assert "get_entity" in template_names
        assert "get_relationships" in template_names

    def test_list_templates_by_category(self):
        """Test filtering templates by category."""
        library = CypherTemplateLibrary()

        # Get traversal templates
        traversal = library.list_templates(category=CypherTemplateCategory.TRAVERSAL)
        for t in traversal:
            assert t["category"] == "traversal"

        # Get entity templates
        entity = library.list_templates(category=CypherTemplateCategory.ENTITY)
        for t in entity:
            assert t["category"] == "entity"

    def test_get_template(self):
        """Test retrieving specific template."""
        library = CypherTemplateLibrary()

        # Get existing template
        template = library.get_template("find_shortest_path")
        assert template is not None
        assert template.name == "find_shortest_path"
        assert "shortestPath" in template.query

        # Get non-existent template
        missing = library.get_template("non_existent_template")
        assert missing is None

    def test_add_custom_template(self):
        """Test adding custom template."""
        library = CypherTemplateLibrary()

        custom = CypherTemplate(
            name="custom_query",
            description="Custom test query",
            query="MATCH (n:Test) RETURN n",
            parameters={},
            category=CypherTemplateCategory.ENTITY,
        )

        library.add_template(custom)

        retrieved = library.get_template("custom_query")
        assert retrieved is not None
        assert retrieved.name == "custom_query"

    def test_label_substitution(self):
        """Test that label parameters are safely substituted."""
        library = CypherTemplateLibrary()

        # Test the internal substitution method
        query = "MATCH (n:$label {id: $entity_id}) RETURN n"
        params = {"label": "User", "entity_id": "user-123"}

        modified_query, remaining_params = library._substitute_label_params(
            query, params
        )

        # Label should be substituted
        assert "$label" not in modified_query
        assert ":User" in modified_query

        # entity_id should remain as parameter
        assert "entity_id" in remaining_params
        assert remaining_params["entity_id"] == "user-123"

    def test_label_validation(self):
        """Test that invalid labels are rejected."""
        library = CypherTemplateLibrary()

        # Try to inject malicious label
        query = "MATCH (n:$label) RETURN n"

        with pytest.raises(ValueError):
            library._substitute_label_params(query, {"label": "User; DROP DATABASE"})

        with pytest.raises(ValueError):
            library._substitute_label_params(query, {"label": "User`DETACH"})

    @pytest.mark.asyncio
    async def test_execute_template(self):
        """Test executing a template with mock Neo4j client."""
        library = CypherTemplateLibrary()

        # Create mock Neo4j client
        mock_neo4j = MagicMock()
        mock_neo4j.run_query = AsyncMock(
            return_value=[{"id": "user-1", "labels": ["User"], "name": "Alice"}]
        )

        # Execute template
        results = await library.execute(
            mock_neo4j,
            "get_entity",
            label="User",
            entity_id="user-1",
        )

        # Verify call
        mock_neo4j.run_query.assert_called_once()
        assert len(results) == 1
        assert results[0]["id"] == "user-1"

    @pytest.mark.asyncio
    async def test_execute_missing_params(self):
        """Test that missing required params raise error."""
        library = CypherTemplateLibrary()
        mock_neo4j = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            await library.execute(
                mock_neo4j,
                "find_shortest_path",
                start_label="User",
                # Missing: start_id, end_label, end_id
            )

        assert "Missing required parameters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_unknown_template(self):
        """Test that unknown template raises error."""
        library = CypherTemplateLibrary()
        mock_neo4j = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            await library.execute(mock_neo4j, "not_a_real_template")

        assert "Template not found" in str(exc_info.value)


class TestDefaultTemplates:
    """Test that default templates have proper structure."""

    def test_all_templates_have_required_fields(self):
        """Verify all default templates have required fields."""
        for name, template in CYPHER_TEMPLATES.items():
            assert template.name == name
            assert template.description, f"{name} missing description"
            assert template.query, f"{name} missing query"
            assert template.category, f"{name} missing category"
            assert isinstance(
                template.parameters, dict
            ), f"{name} has invalid parameters"

    def test_traversal_templates_have_depth_limits(self):
        """Ensure traversal templates don't allow unbounded traversal."""
        traversal_templates = [
            t
            for t in CYPHER_TEMPLATES.values()
            if t.category == CypherTemplateCategory.TRAVERSAL
        ]

        for template in traversal_templates:
            # Check for bounded path patterns
            query = template.query.lower()
            if "*" in query:
                # Should have a limit like *..15 or *1..5
                assert (
                    ".." in query or "limit" in query
                ), f"{template.name} has unbounded traversal"

    def test_all_templates_return_something(self):
        """Verify all templates have RETURN clause."""
        for name, template in CYPHER_TEMPLATES.items():
            assert (
                "RETURN" in template.query.upper() or "return" in template.query
            ), f"{name} missing RETURN clause"


class TestSingletonFactory:
    """Test singleton factory functions."""

    def test_get_template_library_singleton(self):
        """Test that get_template_library returns singleton."""
        lib1 = get_template_library()
        lib2 = get_template_library()
        assert lib1 is lib2

    @pytest.mark.asyncio
    async def test_execute_template_convenience(self):
        """Test convenience execute_template function."""
        mock_neo4j = MagicMock()
        mock_neo4j.run_query = AsyncMock(return_value=[])

        results = await execute_template(
            mock_neo4j,
            "count_by_label",
            label="User",
        )

        assert results == []
        mock_neo4j.run_query.assert_called_once()
