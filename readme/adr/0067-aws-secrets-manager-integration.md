# ADR 0067: AWS Secrets Manager Integration

- **Status**: Accepted
- **Date**: 2026-01-25
- **Deciders**: Igor Beylin, L9 Architecture Team
- **GMP**: GMP-122, GMP-123

## Context and Problem Statement

L9 requires secure management of sensitive credentials including:
- Database connection strings (PostgreSQL, Neo4j, Redis)
- API keys (OpenAI, Anthropic, Slack)
- MCP authentication keys
- JWT secrets

Currently, secrets are stored in `.env` files and environment variables, which:
- Risk accidental commits to version control
- Don't support rotation without redeployment
- Lack audit trail for secret access
- Don't scale across multiple environments

## Decision Drivers

- **Security**: Centralized, encrypted secret storage
- **Rotation**: Support for automatic secret rotation
- **Audit**: Access logging for compliance
- **Flexibility**: Graceful fallback for local development
- **Cost**: Reasonable pricing for small-scale usage

## Considered Options

1. **Environment variables only**: Simple but insecure, no rotation
2. **HashiCorp Vault**: Full-featured but complex to operate
3. **AWS Secrets Manager**: Managed, integrated with AWS ecosystem
4. **1Password Secrets Automation**: Good UX but additional dependency

## Decision Outcome

Chosen option: **AWS Secrets Manager** with environment variable fallback, because it provides the best balance of security, manageability, and AWS ecosystem integration.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Startup                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   L9_SECRETS_PROVIDER=aws?                                  │
│   ┌────────┐                    ┌────────────────┐          │
│   │   Yes  │───────────────────►│ AwsSecretsClient│          │
│   └────────┘                    │  - boto3       │          │
│                                 │  - Cache (1h)  │          │
│                                 │  - Fallback    │          │
│                                 └────────────────┘          │
│   ┌────────┐                    ┌────────────────┐          │
│   │   No   │───────────────────►│ EnvSecretsClient│          │
│   └────────┘                    │  - os.getenv() │          │
│                                 └────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Secret Naming Convention

```
l9/{KEY_NAME}
```

### Complete Secret Inventory (21 secrets as of 2026-01-25)

| Category | Secret | Description |
|----------|--------|-------------|
| **Infrastructure** | `l9/DATABASE_URL` | PostgreSQL connection string |
| | `l9/MEMORY_DSN` | Memory service DSN |
| | `l9/NEO4J_PASSWORD` | Neo4j graph database |
| | `l9/POSTGRES_PASSWORD` | PostgreSQL password |
| **LLM APIs** | `l9/OPENAI_API_KEY` | OpenAI GPT-4 |
| | `l9/ANTHROPIC_API_KEY` | Anthropic Claude |
| | `l9/PERPLEXITY_API_KEY` | Perplexity research |
| **Authentication** | `l9/MCP_API_KEY` | Main MCP key |
| | `l9/MCP_API_KEY_C` | Cursor agent MCP |
| | `l9/MCP_API_KEY_L` | L agent MCP |
| | `l9/L9_EXECUTOR_API_KEY` | VPS executor auth |
| **Slack** | `l9/SLACK_BOT_TOKEN` | Bot OAuth token |
| | `l9/SLACK_SIGNING_SECRET` | Request signing |
| | `l9/SLACK_CLIENT_SECRET` | OAuth client |
| | `l9/SLACK_VERIFICATION_TOKEN` | Legacy verification |
| **Communication** | `l9/TWILIO_AUTH_TOKEN` | Twilio API auth |
| | `l9/TWILIO_ACCOUNT_SID` | Twilio account |
| **Third-Party** | `l9/GOOGLE_CALENDAR_API_KEY` | Calendar integration |
| | `l9/GMAIL_API_KEY` | Email integration |
| **Observability** | `l9/GRAFANA_PASSWORD` | Dashboard admin |
| **Signing** | `l9/GPG_KEY` | GPG signing key |

### Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `L9_SECRETS_PROVIDER` | `env` | Provider: `env` or `aws` |
| `AWS_REGION` | `us-east-1` | AWS region |
| `AWS_SECRETS_PREFIX` | `l9` | Secret name prefix |
| `AWS_SECRETS_CACHE_TTL` | `3600` | Cache TTL in seconds |
| `AWS_SECRETS_FALLBACK_TO_ENV` | `true` (non-prod) | Fallback to env vars |

### Caching Strategy

- **TTL**: 1 hour (configurable via `AWS_SECRETS_CACHE_TTL`)
- **Invalidation**: Manual via `invalidate_cache()` method
- **Cache hits**: ~95% API call reduction in production

## Implementation

### Modules Created

| Module | Purpose |
|--------|---------|
| `core/secrets/__init__.py` | Factory: `get_secrets_client()` |
| `core/secrets/env_secrets_client.py` | Environment variable provider |
| `core/secrets/aws_secrets_client.py` | AWS Secrets Manager client |
| `scripts/secrets/setup_secrets_manager.sh` | One-time setup script |

### Usage

```python
from core.secrets import get_secret, get_secret_or_env

# Simple retrieval
api_key = get_secret("OPENAI_API_KEY")

# With explicit env fallback
db_url = get_secret_or_env("DATABASE_URL", default="postgresql://localhost/l9")
```

### Setup Commands

```bash
# One-time: populate AWS from current .env
./scripts/secrets/setup_secrets_manager.sh --env prod --region us-east-1

# Enable AWS provider in production
export L9_SECRETS_PROVIDER=aws
```

## Positive Consequences

- Centralized secret management with encryption at rest
- Support for secret rotation without redeployment
- Audit trail via AWS CloudTrail
- Graceful fallback for local development
- Reduced risk of accidental secret exposure

## Negative Consequences

- AWS dependency and vendor lock-in
- Additional latency for first secret access (cached thereafter)
- Requires IAM configuration
- Cost (~$0.40/secret/month + API calls)

## IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:s3:::l9/*"
    }
  ]
}
```

For setup script (additional):
```json
{
  "Action": [
    "secretsmanager:CreateSecret",
    "secretsmanager:PutSecretValue",
    "secretsmanager:TagResource"
  ]
}
```

## Rollback Strategy

If issues arise in production:
1. Set `L9_SECRETS_PROVIDER=env` (or unset to default)
2. Redeploy services
3. App reverts to env-var resolution automatically
4. No code changes needed; configuration-only change

## Related

- ADR 0038: Secrets Management Protocol (defines `SecretsClient` protocol)
- ADR 0066: AWS S3 Storage Architecture
- `core/protocols/secrets_protocols.py` - Protocol definition
- Commit: `712c7847` (GMP-122)
- GMP-123: Extended coverage from 9 to 21 secrets
