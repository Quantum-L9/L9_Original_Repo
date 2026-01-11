#!/bin/bash
# =============================================================================
# L9 Agent Executor Deployment Script
# =============================================================================
# 
# Purpose: Deploy and verify agent_executor fix on a server (VPS or local)
# 
# This script is NOT for bootstrapping Slack at server boot - that's handled
# by api/server.py's lifespan() function. This script is for:
#   - Installing dependencies on a fresh server
#   - Verifying the fix is correctly applied
#   - Validating environment configuration
#   - Pre-deployment validation
#
# Usage:
#   ./scripts/deploy_agent_executor.sh
# =============================================================================

set -e  # Exit on error

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  L9 Agent Executor Deployment & Verification                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Get the repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "Repository root: $REPO_ROOT"
echo ""

# Step 1: Install dependencies
echo "Step 1: Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    echo "✓ Dependencies installed"
else
    echo "✗ requirements.txt not found!"
    exit 1
fi
echo ""

# Step 2: Run verification script
echo "Step 2: Running verification script..."
if [ -f "scripts/verify_agent_executor.py" ]; then
    python3 scripts/verify_agent_executor.py
    VERIFY_EXIT=$?
    
    if [ $VERIFY_EXIT -ne 0 ]; then
        echo ""
        echo "✗ Verification failed. Please review errors above."
        exit 1
    fi
    echo "✓ Verification passed"
else
    echo "✗ Verification script not found: scripts/verify_agent_executor.py"
    exit 1
fi
echo ""

# Step 3: Check environment configuration
echo "Step 3: Checking environment configuration..."
if [ -f ".env" ]; then
    if grep -q "L9_ENABLE_LEGACY_SLACK_ROUTER" .env; then
        LEGACY_VALUE=$(grep "L9_ENABLE_LEGACY_SLACK_ROUTER" .env | cut -d'=' -f2 | tr -d ' ')
        echo "  L9_ENABLE_LEGACY_SLACK_ROUTER=$LEGACY_VALUE"
        
        if [ "$LEGACY_VALUE" = "false" ] || [ "$LEGACY_VALUE" = "False" ]; then
            echo "  ⚠ New Slack routing is enabled - agent_executor MUST initialize successfully"
            echo "  ✓ Health check will prevent server start if agent_executor fails"
        else
            echo "  ✓ Legacy Slack routing enabled - agent_executor optional"
        fi
    else
        echo "  ⚠ L9_ENABLE_LEGACY_SLACK_ROUTER not set in .env (defaults to False)"
        echo "  This means new Slack routing is enabled - agent_executor MUST initialize"
        echo "  ✓ Health check will prevent server start if agent_executor fails"
    fi
else
    echo "  ⚠ .env file not found"
    echo "  Default behavior: L9_ENABLE_LEGACY_SLACK_ROUTER=False (new routing enabled)"
    echo "  ✓ Health check will prevent server start if agent_executor fails"
fi
echo ""

# Final summary
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Deployment Verification Complete                              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "1. Restart your L9 server:"
echo "   pkill -f 'uvicorn.*server:app'  # Stop current server"
echo "   uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload  # Start server"
echo ""
echo "2. Check startup logs for:"
echo "   ✓ Agent Executor initialized"
echo "   ✓ Health Check PASSED: Agent Executor is available for Slack routing"
echo ""
echo "3. Test Slack integration:"
echo "   - Send a DM to L on Slack: 'Hello L'"
echo "   - Verify you receive a response (not an error)"
echo "   - Check logs for 'slack_l_agent_response' entries"
echo ""
echo "If you see initialization errors:"
echo "- Check that all kernel files exist in private/kernels/00_system/"
echo "- Verify database connectivity (Neo4j, PostgreSQL)"
echo "- Ensure all environment variables are set correctly"
echo ""

