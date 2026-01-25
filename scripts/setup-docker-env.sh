#!/usr/bin/env bash
# =============================================================================
# L9 Docker Environment Setup Script
# =============================================================================
# component_name: "Docker Setup"
# module_version: "1.0.0"
# created_by: "Manus AI"
# created_at: "2026-01-25T12:00:00Z"
# layer: "operations"
# domain: "docker"
# type: "script"
# status: "active"
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}L9 Docker Environment Setup${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file already exists!${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}✅ Keeping existing .env file${NC}"
        exit 0
    fi
fi

# Copy template
echo -e "${GREEN}📝 Creating .env from .env.docker template...${NC}"
cp .env.docker .env

# Generate secure passwords
echo -e "${GREEN}🔐 Generating secure passwords...${NC}"

# Generate random passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
NEO4J_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
GRAFANA_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
L9_API_KEY=$(openssl rand -hex 32)
L9_EXECUTOR_API_KEY=$(openssl rand -hex 32)
MCP_API_KEY_L=$(openssl rand -hex 32)
MCP_API_KEY_C=$(openssl rand -hex 32)
MCP_API_KEY=$(openssl rand -hex 32)

# Replace placeholders
sed -i.bak "s/CHANGE_ME_SECURE_PASSWORD_HERE/${POSTGRES_PASSWORD}/g" .env
sed -i.bak "s/CHANGE_ME_NEO4J_PASSWORD_HERE/${NEO4J_PASSWORD}/g" .env
sed -i.bak "s/CHANGE_ME_GRAFANA_PASSWORD_HERE/${GRAFANA_PASSWORD}/g" .env
sed -i.bak "s/YOUR_L9_API_KEY_HERE/${L9_API_KEY}/g" .env
sed -i.bak "s/YOUR_EXECUTOR_API_KEY_HERE/${L9_EXECUTOR_API_KEY}/g" .env
sed -i.bak "s/YOUR_MCP_KEY_L_HERE/${MCP_API_KEY_L}/g" .env
sed -i.bak "s/YOUR_MCP_KEY_C_HERE/${MCP_API_KEY_C}/g" .env
sed -i.bak "s/YOUR_MCP_KEY_HERE/${MCP_API_KEY}/g" .env

# Remove backup file
rm -f .env.bak

echo -e "${GREEN}✅ Secure passwords generated!${NC}"
echo ""

# Prompt for OpenAI API key
echo -e "${YELLOW}🔑 OpenAI API Key Required${NC}"
echo "Please enter your OpenAI API key (or press Enter to skip):"
read -r OPENAI_KEY

if [ -n "$OPENAI_KEY" ]; then
    sed -i.bak "s/YOUR_OPENAI_API_KEY_HERE/${OPENAI_KEY}/g" .env
    rm -f .env.bak
    echo -e "${GREEN}✅ OpenAI API key configured${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping OpenAI API key (you can add it later in .env)${NC}"
fi

echo ""

# Prompt for Perplexity API key (optional)
echo -e "${YELLOW}🔑 Perplexity API Key (Optional)${NC}"
echo "Please enter your Perplexity API key (or press Enter to skip):"
read -r PERPLEXITY_KEY

if [ -n "$PERPLEXITY_KEY" ]; then
    sed -i.bak "s/YOUR_PERPLEXITY_KEY_HERE/${PERPLEXITY_KEY}/g" .env
    rm -f .env.bak
    echo -e "${GREEN}✅ Perplexity API key configured${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping Perplexity API key${NC}"
fi

echo ""
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""
echo "Generated credentials:"
echo "  📊 PostgreSQL password: ${POSTGRES_PASSWORD}"
echo "  🗄️  Neo4j password: ${NEO4J_PASSWORD}"
echo "  📈 Grafana password: ${GRAFANA_PASSWORD}"
echo "  🔑 L9 API key: ${L9_API_KEY}"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Save these credentials securely!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review and customize .env if needed"
echo "  2. Start containers: docker compose up -d"
echo "  3. Check status: docker compose ps"
echo "  4. View logs: docker compose logs -f"
echo ""
echo "Access points:"
echo "  🌐 L9 API: http://localhost:8000"
echo "  🧠 MCP Memory: http://localhost:9002"
echo "  📊 Prometheus: http://localhost:9090"
echo "  📈 Grafana: http://localhost:3000 (admin/${GRAFANA_PASSWORD})"
echo "  🔍 Jaeger: http://localhost:16686"
echo "  🗄️  Neo4j Browser: http://localhost:7474 (neo4j/${NEO4J_PASSWORD})"
echo ""
echo -e "${GREEN}Happy hacking! 🚀${NC}"
