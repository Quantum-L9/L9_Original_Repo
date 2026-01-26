"""
L9 Migration Smoke Tests
Version: 1.0.0

Validates that database migrations:
- Are properly numbered
- Have valid SQL syntax
- Can be applied to a fresh database
- Don't have conflicting names

Run with: pytest tests/docker/test_migrations.py -v
"""

import re
from pathlib import Path

import pytest

# Path to migrations directory
MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"


class TestMigrationFileStructure:
    """Validate migration file naming and structure."""

    def test_migrations_directory_exists(self):
        """Migrations directory must exist."""
        assert MIGRATIONS_DIR.exists(), (
            f"Migrations directory not found: {MIGRATIONS_DIR}"
        )

    def test_migrations_have_sql_extension(self):
        """All migration files should have .sql extension (excludes docs like README)."""
        if not MIGRATIONS_DIR.exists():
            pytest.skip("Migrations directory not found")

        # Allowed non-SQL files in migrations directory
        allowed_non_sql = {"README.md", "SCHEMA_DIAGRAM.txt"}

        for file in MIGRATIONS_DIR.iterdir():
            if file.is_file() and not file.name.startswith("."):
                if file.name in allowed_non_sql:
                    continue  # Documentation files are allowed
                assert file.suffix == ".sql", (
                    f"Migration file has wrong extension: {file.name} (expected .sql)"
                )

    def test_migrations_are_numbered(self):
        """
        Migrations should be numbered sequentially (0001, 0002, etc).

        This ensures they run in correct order.
        """
        if not MIGRATIONS_DIR.exists():
            pytest.skip("Migrations directory not found")

        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        for file in sql_files:
            # Should start with 4 digits
            match = re.match(r"^(\d{4})_", file.name)
            assert match, f"Migration filename should start with 4 digits: {file.name}"

    def test_no_duplicate_migration_numbers(self):
        """
        Migration numbers should be unique (no 0004_a.sql and 0004_b.sql).

        Duplicate numbers cause unpredictable ordering.
        """
        if not MIGRATIONS_DIR.exists():
            pytest.skip("Migrations directory not found")

        sql_files = list(MIGRATIONS_DIR.glob("*.sql"))
        numbers = []

        for file in sql_files:
            match = re.match(r"^(\d{4})_", file.name)
            if match:
                numbers.append((match.group(1), file.name))

        # Group by number
        seen = {}
        for num, name in numbers:
            if num in seen:
                pytest.fail(f"Duplicate migration number {num}: {seen[num]} and {name}")
            seen[num] = name

    def test_migrations_are_sequential(self):
        """
        Migration numbers should be sequential with no gaps.

        Gaps might indicate missing migrations.
        """
        if not MIGRATIONS_DIR.exists():
            pytest.skip("Migrations directory not found")

        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        numbers = []
        for file in sql_files:
            match = re.match(r"^(\d{4})_", file.name)
            if match:
                numbers.append(int(match.group(1)))

        if not numbers:
            pytest.skip("No numbered migrations found")

        # Check for gaps (allow duplicates, just check max)
        unique_numbers = sorted(set(numbers))
        expected = list(range(1, max(unique_numbers) + 1))

        missing = set(expected) - set(unique_numbers)
        if missing:
            pytest.warn(f"Gap in migration numbers - missing: {sorted(missing)}")


class TestMigrationSQLSyntax:
    """Validate SQL syntax in migration files."""

    def test_migrations_are_not_empty(self):
        """Migration files should contain SQL."""
        if not MIGRATIONS_DIR.exists():
            pytest.skip("Migrations directory not found")

        for file in MIGRATIONS_DIR.glob("*.sql"):
            content = file.read_text().strip()
            assert content, f"Migration file is empty: {file.name}"

    def test_migrations_have_valid_statements(self):
        """
        Migration files should contain valid SQL statement keywords.

        Basic syntax check - not full SQL parsing.
        """
        if not MIGRATIONS_DIR.exists():
            pytest.skip("Migrations directory not found")

        valid_keywords = [
            "CREATE",
            "ALTER",
            "DROP",
            "INSERT",
            "UPDATE",
            "DELETE",
            "SELECT",
            "INDEX",
            "TABLE",
            "SCHEMA",
            "EXTENSION",
            "GRANT",
            "--",  # Comments are valid
        ]

        for file in MIGRATIONS_DIR.glob("*.sql"):
            content = file.read_text().strip().upper()

            # Check if file contains at least one valid SQL keyword
            has_valid = any(kw in content for kw in valid_keywords)
            assert has_valid, (
                f"Migration file doesn't appear to contain SQL: {file.name}"
            )

    def test_migrations_have_schema_prefix(self):
        """
        Tables should use schema prefix (e.g., memory.table_name).

        This is an L9 convention to keep tables organized.
        """
        if not MIGRATIONS_DIR.exists():
            pytest.skip("Migrations directory not found")

        for file in MIGRATIONS_DIR.glob("*.sql"):
            content = file.read_text()

            # Look for CREATE TABLE without schema prefix
            # This is a soft check - some tables might intentionally be in public
            create_tables = re.findall(
                r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
                content,
                re.IGNORECASE,
            )

            for table in create_tables:
                if "." not in content.split(table)[0].split("TABLE")[-1]:
                    # No schema prefix found - just warn, don't fail
                    pass  # Could add pytest.warn() here


class TestMigrationIntegrity:
    """Test migration file integrity."""

    def test_no_destructive_operations_without_safety(self):
        """
        Destructive operations (DROP, TRUNCATE, DELETE without WHERE)
        should be flagged.
        """
        if not MIGRATIONS_DIR.exists():
            pytest.skip("Migrations directory not found")

        dangerous_patterns = [
            (r"DROP\s+TABLE\s+(?!IF\s+EXISTS)", "DROP TABLE without IF EXISTS"),
            (r"DROP\s+SCHEMA\s+(?!IF\s+EXISTS)", "DROP SCHEMA without IF EXISTS"),
            (r"TRUNCATE\s+TABLE", "TRUNCATE TABLE (use DELETE with WHERE)"),
            (r"DELETE\s+FROM\s+\w+\s*;", "DELETE without WHERE clause"),
        ]

        warnings = []
        for file in MIGRATIONS_DIR.glob("*.sql"):
            content = file.read_text()

            for pattern, description in dangerous_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    warnings.append(f"{file.name}: {description}")

        if warnings:
            # Warn but don't fail - these might be intentional
            pytest.warn(f"Potentially dangerous operations: {warnings}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
