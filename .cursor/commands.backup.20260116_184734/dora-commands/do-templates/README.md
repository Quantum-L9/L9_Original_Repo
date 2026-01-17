# Project Name

> DORA-aligned project initialized with `/do-init`

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Run linter
ruff check .

# Start local development
docker-compose up -d
```

## DORA Workflow Commands

| Command | Purpose |
|---------|---------|
| `/do-status` | See current project state and context |
| `/do-next` | Get the next task from DORA Checklist |
| `/do-deploy` | Execute deployment with metrics tracking |
| `/do-metrics` | View DORA metrics dashboard |
| `/do-end` | Log session and prepare handoff |

## Project Structure

```
.
├── .dora/                  # DORA state and metrics
│   ├── state.yaml          # Project phase and progress
│   ├── metrics.yaml        # DORA metrics data
│   └── session-log.md      # Session history
├── .github/workflows/      # CI/CD pipeline
├── src/                    # Application source code
├── tests/                  # Test suite
├── docker-compose.yaml     # Local dev stack
├── Dockerfile              # Container definition
├── pyproject.toml          # Python configuration
└── .pre-commit-config.yaml # Pre-commit hooks
```

## DORA Metrics

Track your DevOps performance:

- **Deployment Frequency**: How often you deploy
- **Lead Time**: Commit to production time
- **Change Failure Rate**: % of deployments causing issues
- **MTTR**: Mean time to recover from failures

Run `/do-metrics` to see your current performance level.

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Linting

```bash
# Check
ruff check .

# Fix automatically
ruff check . --fix

# Format
ruff format .
```

### Docker

```bash
# Build
docker build -t app:dev .

# Run
docker-compose up -d

# Logs
docker-compose logs -f app
```

## License

MIT

