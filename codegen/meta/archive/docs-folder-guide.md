<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# What else goes in docs folder?

Beyond `architecture.md` and `ai-collaboration.md`, a gold-standard `docs/` folder usually carries a few more **purpose-specific** documents.[^1]

## Process and governance docs

These explain how changes happen and how agents are supposed to behave.[^1]

- **`governance.md`**
    - Decision-making, ownership, approval flows.
    - Rules for high-risk changes (infra, security, data model).
- **`operational-playbooks/`** (directory)
    - `oncall-runbook.md`: what to do when core services break.
    - `incident-response.md`: incident levels, comms channels, timeline expectations.
- **`contributing.md`** (can live at root but linked from `docs/`)
    - Branching, PR flow, review standards, code style, commit message format.


## Domain and capability docs

These give deeper context for agents, tools, and memory.[^1]

- **`capabilities.md`**
    - Human-readable summary of what the system can and cannot do (per subsystem/agent).
    - Pointers to manifests (JSON/YAML) that are the machine-readable source of truth.
- **`memory-and-tools.md`**
    - Overview of memory layers (short-term, long-term, audit).
    - How tools interact with memory and what invariants must hold.
- **`agents.md`**
    - Brief profiles for major agents (roles, responsibilities, delegation rules).
    - Links to their kernel/manifest files.


## Runbooks and procedures

These are “how-to” guides for recurring tasks.[^1]

- **`deployments.md`**
    - Step-by-step deployment procedures (dev/stage/prod).
    - Rollback procedures and sanity checks.
- **`maintenance-tasks.md`**
    - Regular housekeeping (index rebuilds, migrations, log rotation).
    - Health checks and capacity planning notes.
- **`troubleshooting.md`**
    - Common failure symptoms and likely causes.
    - Commands and dashboards to inspect first.


## Design and decision records

These preserve why things are the way they are.[^1]

- **`adr/`** (Architecture Decision Records)
    - One file per major decision: context, options, decision, consequences.
    - Linked from `architecture.md` where relevant.
- **`roadmap.md`**
    - Near-term and medium-term planned changes.
    - Flags for upcoming breaking changes.


## API and integration docs

These are especially useful when uploading to AI so it understands all surfaces.[^1]

- **`api/`**
    - `http-api.md`: main REST/WebSocket endpoints, auth, example requests.
    - `webhooks.md`: inbound/outbound webhook contracts.
- **`integrations.md`**
    - External systems (Slack, Mac agent, MCP servers, databases).
    - What’s considered core vs optional.

If you want, the next step can be: list your intended `docs/` files and directories, and a concrete, filled-out template can be drafted for each one tailored to your L9 stack and governance model.[^1]

<div align="center">⁂</div>

[^1]: can-u-act-as-a-tutor-and-expla-kGNhGCDyQDWqsE9k2ujtjw.md

