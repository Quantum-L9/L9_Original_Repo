# CI: Using repo/organization Secrets for DB and Neo4j

This doc explains how to add **repository or organization Secrets** in GitHub and pass them into CI jobs so workflows can use a real test DB and Neo4j when needed.

## 1. Add secrets in GitHub

- **Repo secrets:** GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
- **Org secrets:** **Organization** → **Settings** → **Secrets and variables** → **Actions** → **New organization secret** (optional, for sharing across repos).

Suggested names and usage:

| Secret name        | Purpose                          | Used by |
|--------------------|----------------------------------|---------|
| `MEMORY_DSN`       | PostgreSQL connection string     | CI test job, docker-smoke (or use in-job Postgres) |
| `NEO4J_URI`        | Neo4j Bolt URL (e.g. `bolt://host:7687`) | Jobs that start the L9 server |
| `NEO4J_USER`       | Neo4j user                      | Optional if URI has auth |
| `NEO4J_PASSWORD`   | Neo4j password                  | Optional if URI has auth |
| `OPENAI_API_KEY`   | OpenAI API key (for some jobs)   | Already used in ci.yml |
| `CODECOV_TOKEN`    | Codecov upload                  | Already used |
| `GITGUARDIAN_API_KEY` | GitGuardian scan              | Already used |

You do **not** need to create these if CI uses **in-job service containers** (Postgres + Neo4j) with fixed test credentials; secrets are for **hosted** DB/Neo4j or real API keys.

## 2. Pass secrets into a job

In `.github/workflows/*.yml`, give a job access to secrets via `env`:

```yaml
jobs:
  my-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Run something that needs DB/Neo4j
        env:
          MEMORY_DSN: ${{ secrets.MEMORY_DSN }}
          NEO4J_URI: ${{ secrets.NEO4J_URI }}
          NEO4J_USER: ${{ secrets.NEO4J_USER }}
          NEO4J_PASSWORD: ${{ secrets.NEO4J_PASSWORD }}
        run: ./scripts/my_script.sh
```

- Only **steps** that need the values should reference `secrets.*`; secrets are not logged.
- If a secret is missing, the value is empty and the step may fail (e.g. server fails to start). Ensure the repo/org has the secret set when the job is required.

## 3. When to use secrets vs service containers

| Approach              | Use when |
|-----------------------|----------|
| **Service containers**| CI runs Postgres/Neo4j in the same workflow (no external host). No secrets needed for DB URLs; use fixed test credentials in the workflow. |
| **Repo/org secrets**  | CI talks to a **hosted** Postgres or Neo4j (e.g. managed cloud). Set `MEMORY_DSN`, `NEO4J_URI`, etc. as secrets and pass them into the job `env` as above. |

L9 CI currently uses **service containers** for the test job (Postgres, Redis) and can add Neo4j the same way so the app can start with fail-closed boot (P0) without storing DB URLs in secrets.
