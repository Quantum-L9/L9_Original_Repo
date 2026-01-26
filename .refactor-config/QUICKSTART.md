# AI-Enabled Refactoring Quick Start Guide

## Phase 1: Setup (30 minutes)

1. Install tools:
   pip install -r .refactor-config/requirements-refactor.txt
   npm install --save-dev (for TypeScript)

2. Install pre-commit hooks:
   pre-commit install

3. Configure AI assistants:
   - Cursor: Open project in Cursor IDE
   - GitHub Copilot: Enable in VS Code/Cursor
   - Claude: Get API key from https://console.anthropic.com

## Phase 2: Quick Wins (Week 1)

1. Auto-format all files:
   ruff check src/ --fix
   black src/
   prettier --write .

2. Remove dead code:
   vulture src/ --min-confidence 80 > dead_code.txt

   # Review then manually remove

3. Run test suite:
   pytest tests/ -v

## Phase 3: AI-Assisted Refactoring (Weeks 2-4)

1. Open Cursor IDE
2. Load refactoring backlog: cat .refactor-reports/backlog.json
3. For each item:
   - Use Cursor Agent Mode (Cmd+K) to plan refactoring
   - Execute changes
   - Run: pytest tests/ + mutmut run
   - Create PR with changes

## Phase 4: Validation (Ongoing)

1. Monitor CI/CD pipeline:

   - GitHub Actions: https://github.com/YOUR_ORG/YOUR_REPO/actions
   - Check mutation score: > 85%
   - Check test coverage: > 80%

2. Review metrics monthly:
   - Technical debt ratio target: < 5%
   - Deployment frequency: target > 4x/week
   - Mean time to recovery: target < 15 min

## Troubleshooting

### AI suggests broken code

→ This is normal! Add more test cases. AI hallucinations are caught by:

- Mutation testing
- Type checking (mypy strict)
- Integration tests

### Tests fail after refactoring

→ Check if change broke contract:

1.  Revert: git checkout <file>
2.  Review change scope: should be < 300 lines
3.  Ask Claude for smaller, atomic refactoring

### Type errors appear

→ Run: mypy src/ --strict
→ Use Cursor to add missing type annotations

## Next Steps

1. Schedule weekly 1-hour refactoring session (Tuesdays 2pm)
2. Assign team member as "Refactoring Champion"
3. Monthly: Review metrics, celebrate improvements, plan next priorities
