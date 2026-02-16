
## GitHub-hosted runners

These are VM instances provided by GitHub.

Use them when:

- You need standard environments (Linux/Windows/macOS) with typical tools.
- Your tests don’t require private network access to your own VPS or databases.
- You’re okay with GitHub’s hardware and concurrency limits for your plan.[^3][^4]
- You want zero maintenance: no patching, scaling, or runner security management.

Good fit for:

- Running `ci_meta_check_and_tests.py`, pytest, lint, type-checks.
- Building and testing containers, simple deployment scripts that push to a public cloud.[^2][^5]


## Self-hosted runners

These are machines you manage (VPS, on-prem, even your Mac) registered as runners.

Use them when:

- You need **access to private infrastructure** that GitHub-hosted runners can’t reach (e.g. internal services, non-public databases, your L9 VPS).
- You require **custom hardware** or OS (GPUs, special CPU features, large RAM disks).
- You have **strict security/compliance** needs where builds must run within your own network or region.[^6][^3]
- You want to avoid GitHub’s minutes limits or need more predictable performance at scale.

Good fit for:

- Running integration/E2E tests against your live-like L9 stack on a private network.
- Running heavy agent simulations or tool orchestration tests that need your actual Redis/Postgres instances.
- Doing in-branch deployments directly to your VPS from a runner on that same VPS.


## Hybrid pattern (likely best for you)

- GitHub-hosted runners:
    - Fast unit tests, meta YAML compliance, lint/type checks on every PR.
- Self-hosted runners:
    - Heavier integration/E2E tests that need your L9 environment.
    - Possibly deployment jobs that must run with access to your private infra.

In short: start with GitHub-hosted for everything, introduce self-hosted only when you clearly need local network access, specialized hardware, or tighter control over where and how your CI runs.