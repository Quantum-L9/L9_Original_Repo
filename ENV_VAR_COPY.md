# =============================================================================
# L9 DOCKER/VPS Environment (.env.vps)
# For Docker Compose on VPS - uses service DNS names (NOT localhost!)
#
# ⚠️  CRITICAL: NO INLINE COMMENTS ALLOWED
#     Pydantic-settings parses entire line as value
# =============================================================================

# -----------------------------------------------------------------------------
# Database (use container service names, NOT localhost/127.0.0.1)
# -----------------------------------------------------------------------------
POSTGRES_USER=postgres
POSTGRES_PASSWORD=8e4fXWM6Q3M87*b3
POSTGRES_DB=l9_memory
MEMORY_DSN=postgresql://postgres:8e4fXWM6Q3M87*b3@l9-postgres:5432/l9_memory
DATABASE_URL=postgresql://postgres:8e4fXWM6Q3M87*b3@l9-postgres:5432/l9_memory

# -----------------------------------------------------------------------------
# API Keys
# -----------------------------------------------------------------------------
L9_EXECUTOR_API_KEY=9c4753df3b7ee85e2370b0e9a55355e59a9cf3c15f65791de4ab8cdd656b4304
L9_API_KEY=9c4753df3b7ee85e2370b0e9a55355e59a9cf3c15f65791de4ab8cdd656b4304
OPENAI_API_KEY=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
PERPLEXITY_API_KEY=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
GOOGLE_CALENDAR_API_KEY=AIzaSyCFHrbriSBBvsCEHn8s-56CH-mUPFtGOCg
GMAIL_API_KEY=AIzaSyCFHrbriSBBvsCEHn8s-56CH-mUPFtGOCg
GPG_KEY=7169605F62C751356D054A26A821E680E5FA6305
L9_API_URL=http://mcp.quantumaipartners.com:30080
# -----------------------------------------------------------------------------
# Neo4j Graph Database (use container name)
# -----------------------------------------------------------------------------
NEO4J_URL=bolt://neo4j:7687
NEO4J_URI=${NEO4J_URL}
NEO4J_USER=neo4j
NEO4J_PASSWORD=FVmgaD1diPcz41zRbYLLP0UzyGvAi4E

# -----------------------------------------------------------------------------
# Redis (use container name)
# -----------------------------------------------------------------------------
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=bBZZ0JYcr6sDj3lWBK0euSLkeGAR7MT5+3PCR5LK+vM=

# -----------------------------------------------------------------------------
# Qdrant Vector Store (use container name)
# -----------------------------------------------------------------------------
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# -----------------------------------------------------------------------------
# Slack Integration
# -----------------------------------------------------------------------------
SLACK_APP_ENABLED=true
SLACK_APP_ID=A0A3MLBJ55Y
SLACK_SIGNING_SECRET=d88113146f7be4c9c63e08fbb6579f9e
SLACK_CLIENT_SECRET=d14377ce8bf1c265f7466188791c2034
SLACK_CLIENT_ID=5756690555681.10123691617202
SLACK_BOT_TOKEN=xoxb-5756690555681-10120570028437-0GsjsVSUP0rsKfxOoHFPrpxc
SLACK_VERIFICATION_TOKEN=nFrKJ0NVekjgzIpOtpyYqUCK
SLACK_BOT_USER_ID=U0A3JGS0UCV
L_SLACK_USER_ID=U0A3JGS0UCV

# -----------------------------------------------------------------------------
# Twilio
# -----------------------------------------------------------------------------
TWILIO_ENABLED=false
TWILIO_ACCOUNT_SID=AC4daa74c868f142472f9717e3ac6c8c0f
TWILIO_AUTH_TOKEN=d3d1d33dd9afb72f36c210dc845a4ea3
TWILIO_SMS_NUMBER=17047416314
TWILIO_WHATSAPP_NUMBER=17047416314

# -----------------------------------------------------------------------------
# API Server Config
# -----------------------------------------------------------------------------
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# -----------------------------------------------------------------------------
# Memory API
# -----------------------------------------------------------------------------
MEMORY_API_PORT=8080
MEMORY_API_BASE_URL=http://l9-memory-api:8080

# -----------------------------------------------------------------------------
# Embedding Config
# -----------------------------------------------------------------------------
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small 

# -----------------------------------------------------------------------------
# Deployment Info
# -----------------------------------------------------------------------------
LOCAL_DEV=false
DOMAIN=l9.quantumaipartners.com
VPS_IP=46.62.243.82

# -----------------------------------------------------------------------------
# MCP Memory Server Authentication
# -----------------------------------------------------------------------------
MCP_API_KEY=65f5ad9d1094de02a586621fa327a1a31eca66cba7b50fa9c68be882ba018689
MCP_L9_MEMORY_KEY=65f5ad9d1094de02a586621fa327a1a31eca66cba7b50fa9c68be882ba018689

# -----------------------------------------------------------------------------
# L9 Agent Identity (GMP-29)
# -----------------------------------------------------------------------------
L9_TENANT_ID=l-cto
L_CTO_USER_ID=l-cto
MCP_API_KEY_L=a8a572de705ecc2f0b2de95bc20a4024fc9f7b23dec825bbf24f71ba8bb563ef

CURSOR_TENANT_ID=cursor-ide
CURSOR_USER_ID=cursor-ide
MCP_API_KEY_C=4836ea7e0f46c81fd6860c05f1be94577fbb99970fb378c49901cc6cffb9dd07

RLS_TENANT_ID=l9
RLS_ORG_ID=quantumai

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------
L9_OBSERVABILITY=true
L9_ENABLE_LEGACY_CHAT=false
L9_ENABLE_LEGACY_SLACK_ROUTER=false
L9_GRAPH_AGENT_STATE=true
L9_GRAPH_WM_SYNC=true
L9_WM_GRAPH_SYNC=true
L9_TOOL_PATTERN_EXTRACTION=true
L9_USE_KERNELS=true
L9_NEW_AGENT_INIT=true
L9_STAGE3_MODULES=true
L9_STAGE4_CONSOLIDATION=true
L9_CONSOLIDATION_INTERVAL_HOURS=4

# -----------------------------------------------------------------------------
# Integration Toggles
# -----------------------------------------------------------------------------
MAC_AGENT_ENABLED=true
EMAIL_ENABLED=false
WABA_ENABLED=false
INBOX_PARSER_ENABLED=false
EMAIL_AGENT_ENABLED=true
L9_EMAIL_MULTI_ACCOUNT=true

# -----------------------------------------------------------------------------
# Governance (Memory Operations)
# -----------------------------------------------------------------------------
GOVERNANCE_HARDENING_ENABLED=True
GOVERNANCE_ENFORCEMENT_MODE=log_only
L9_SKIP_STARTUP_CHECKS=false

# -----------------------------------------------------------------------------
# Docker Build Metadata (required by docker-compose.prod.yml)
# -----------------------------------------------------------------------------
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
VERSION=4.1.0
COMPOSE_PROJECT_NAME=l9
DOCKER_REGISTRY=ghcr.io
DOCKER_NAMESPACE=cryptoxdog
L9_API_PORT=8000
MCP_PORT=9002

GRAFANA_PASSWORD=admin123secure
