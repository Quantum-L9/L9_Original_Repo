# L9 AI PR Review Workflow

## Overview
Automated dual-AI review system with auto-applied code improvements.

## Pipeline Stages

### Stage 1: Gemini Code Assist (GitHub App)
- **Trigger**: Automatic on PR open/update
- **Action**: Reviews code against `.gemini/styleguide.md`
- **Output**: Inline suggestions posted as PR comments

### Stage 2: Gemini API Auto-Apply
- **Trigger**: After Gemini app review completes
- **Action**: Calls Gemini API to get improvements, applies them automatically
- **Output**: Commits pushed to PR branch

### Stage 3: Perplexity Deep Audit
- **Trigger**: After Gemini changes are applied
- **Action**: Comprehensive security, performance, architecture audit
- **Output**: Audit report + additional fixes committed

## Configuration

### Gemini Code Assist Setup
1. Install **Gemini Code Assist GitHub App** on repository
2. Ensure `.gemini/styleguide.md` exists (contains L9-specific rules)
3. App auto-reviews all PRs (no manual trigger needed)

### API Keys (Repository Secrets)
```bash
GEMINI_API_KEY=AIzaSyA-Muh1S1Yj4nHTYiTNJbiVWP0PAxI5YCE
PERPLEXITY_API_KEY=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
```

### Protected Files

These files require explicit human approval before modification:

- `api/websocket_orchestrator.py`
- `docker-compose.yml`
- `core/kernel_loader.py`
- `memory/substrate_service.py`
- `core/schemas/packet_envelope.py`

## Manual Controls

### Disable Auto-Fix for Specific PR

Add label: `ai-review:manual`

### Request Re-Review

Comment on PR: `/gemini review` or `/perplexity audit`

### Skip Audit

Add label: `skip-ai-review`

## Metrics

- Average review time: ~3-5 minutes per PR
- Auto-fix success rate: ~85%
- False positive rate: <5%
