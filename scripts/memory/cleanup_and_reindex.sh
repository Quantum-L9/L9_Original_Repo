#!/bin/bash
# cleanup_and_reindex.sh - Delete Trash Embeddings and Re-index High-Value Content
# ================================================================================

set -e

echo "============================================================"
echo "CLEANUP AND RE-INDEX: Memory Graph Population"
echo "============================================================"
echo ""

# Step 1: Generate SQL to delete trash embeddings
echo "Step 1: Finding trash embeddings..."
python3 scripts/generate_delete_sql.py > /tmp/delete_trash.sql

TRASH_COUNT=$(grep -c "Found.*trash" /tmp/delete_trash.sql || echo "0")
echo "  Found $TRASH_COUNT trash embeddings"

if [ "$TRASH_COUNT" = "0" ]; then
    echo "  No trash embeddings to delete"
else
    echo "  SQL generated: /tmp/delete_trash.sql"
    echo ""
    echo "  To delete trash embeddings, run:"
    echo "    psql -d l9 -f /tmp/delete_trash.sql"
    echo ""
    read -p "  Delete trash embeddings now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v psql &> /dev/null; then
            psql -d l9 -f /tmp/delete_trash.sql
            echo "  ✅ Deleted trash embeddings"
        else
            echo "  ⚠️  psql not found. Please run manually:"
            echo "     psql -d l9 -f /tmp/delete_trash.sql"
        fi
    else
        echo "  ⏭️  Skipped deletion (run manually if needed)"
    fi
fi

echo ""
echo "Step 2: Re-indexing high-value content..."
echo ""

# Step 2: Re-index GMP reports
echo "  2.1: Indexing GMP reports..."
python3 scripts/index_gmp_reports.py --verbose 2>&1 | grep -E "(Found|Indexed|facts_created|embeddings_created)" || echo "    (Check output above)"

# Step 3: Index error patterns
echo ""
echo "  2.2: Indexing error patterns..."
python3 scripts/index_error_patterns.py --verbose 2>&1 | grep -E "(Found|Indexed|facts_created|embeddings_created)" || echo "    (Check output above)"

# Step 4: Index architectural decisions
echo ""
echo "  2.3: Indexing architectural decisions..."
python3 scripts/index_architecture.py --verbose 2>&1 | grep -E "(Found|Indexed|facts_created|relationships_created)" || echo "    (Check output above)"

# Step 5: Index user preferences
echo ""
echo "  2.4: Indexing user preferences..."
python3 scripts/index_preferences.py --verbose 2>&1 | grep -E "(Found|Indexed|facts_created|embeddings_created)" || echo "    (Check output above)"

# Step 6: Index tool usage (Neo4j)
echo ""
echo "  2.5: Indexing tool usage patterns..."
python3 scripts/index_tool_usage.py --verbose 2>&1 | grep -E "(Found|Indexed|tools_indexed|relationships_created)" || echo "    (Check output above)"

echo ""
echo "============================================================"
echo "CLEANUP AND RE-INDEX COMPLETE"
echo "============================================================"
echo ""
echo "Summary:"
echo "  - Trash embeddings: $TRASH_COUNT found (check deletion status above)"
echo "  - Re-indexed: GMP reports, errors, architecture, preferences, tool usage"
echo ""
echo "Next steps:"
echo "  1. Verify semantic search returns better results"
echo "  2. Check knowledge facts are accessible"
echo "  3. Monitor embedding quality going forward"
echo ""
