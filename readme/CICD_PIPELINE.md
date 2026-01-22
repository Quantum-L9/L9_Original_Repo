# L9 Automated CI/CD Pipeline

**Version:** 1.0  
**Date:** 2026-01-20  
**Status:** Active

---

## A. Overview

This document provides a comprehensive guide to the L9 automated CI/CD pipeline. This pipeline enables the L9 agent to autonomously test, build, and deploy new versions of itself and other services, unlocking true autonomy and self-improvement.

### Key Features

-   **Automated Testing:** Runs a comprehensive test suite in an isolated environment.
-   **Docker Image Building:** Builds and pushes Docker images to the GitHub Container Registry.
-   **Security Scanning:** Scans Docker images for vulnerabilities using Trivy.
-   **Automated Deployment:** Deploys to staging and production environments with manual approval for production.
-   **Agent-Triggered Deployments:** The L9 agent can trigger deployments using a new `trigger_deployment` tool.
-   **Health Checks and Rollbacks:** Includes pre- and post-deployment health checks with automated rollbacks on failure.

---

## B. Pipeline Architecture

The CI/CD pipeline is composed of two main workflows:

1.  **`ci-build.yml`:** Continuous Integration and Build
2.  **`cd-deploy.yml`:** Continuous Deployment

### `ci-build.yml` Workflow

This workflow runs on every push to `main` and `develop`, and on every pull request to `main`.

**Jobs:**

1.  **`test`:**
    -   Starts an isolated test environment using `docker-compose.test.yml`.
    -   Runs the full test suite, including unit, integration, and contract tests.

2.  **`build`:**
    -   Builds Docker images for `l9-api` and `l9-mcp-memory`.
    -   Tags images with Git branch, PR number, semantic version, and commit SHA.
    -   Pushes images to the GitHub Container Registry (`ghcr.io`).

3.  **`security-scan`:**
    -   Scans the newly built Docker images for vulnerabilities using Trivy.
    -   Uploads results to the GitHub Security tab.

### `cd-deploy.yml` Workflow

This workflow runs when a new release is published, or when triggered manually or by the L9 agent.

**Jobs:**

1.  **`deploy-staging`:**
    -   Deploys the latest Docker images to the staging environment.
    -   Runs pre- and post-deployment health checks.
    -   Runs smoke tests against the staging environment.

2.  **`deploy-production`:**
    -   Requires manual approval before running.
    -   Deploys the specified Docker image tag to the production environment.
    -   Includes a blue-green deployment strategy for zero-downtime deployments.
    -   Creates a deployment backup before deploying.
    -   Runs health checks and automatically rolls back on failure.

3.  **`rollback`:**
    -   Automatically triggers on failure of `deploy-staging` or `deploy-production`.
    -   Rolls back to the previous stable deployment.

---

## C. Agent-Triggered Deployments

The L9 agent can autonomously trigger deployments using the new `trigger_deployment` tool.

### `trigger_deployment` Tool

**Usage:**

```python
from tools.deployment import trigger_deployment

# Trigger a deployment to staging
response = await trigger_deployment("staging", "v2.4.0")

# Check the deployment status
status = await check_deployment_status(response.workflow_run_id)
```

This tool allows the agent to:

-   Deploy new versions of itself after making improvements.
-   Deploy new services that it has created.
-   Roll back to a previous version if it detects a problem.

### Authentication

The `trigger_deployment` tool uses a GitHub personal access token with `repo` and `workflow` scopes. This token must be stored in the `GITHUB_TOKEN` environment variable.

---

## D. Deployment Scripts

The deployment process is managed by a set of shell scripts in the `scripts/deployment/` directory:

-   **`pre_deploy_check.sh`:** Runs before deployment to ensure the system is healthy.
-   **`post_deploy_check.sh`:** Runs after deployment to verify the new version.
-   **`rollback_deployment.sh`:** Rolls back to the previous stable deployment.
-   **`create_deployment_backup.sh`:** Creates a backup of the current deployment.
-   **`blue_green_deploy.sh`:** Implements a blue-green deployment strategy.

---

## E. Environment Configuration

### GitHub Secrets

The following secrets must be configured in the GitHub repository settings:

-   `STAGING_HOST`: Hostname or IP address of the staging server.
-   `STAGING_USER`: SSH username for the staging server.
-   `STAGING_SSH_KEY`: SSH private key for the staging server.
-   `STAGING_PATH`: Absolute path to the L9 deployment directory on the staging server.
-   `PRODUCTION_HOST`: Hostname or IP address of the production server.
-   `PRODUCTION_USER`: SSH username for the production server.
-   `PRODUCTION_SSH_KEY`: SSH private key for the production server.
-   `PRODUCTION_PATH`: Absolute path to the L9 deployment directory on the production server.
-   `GITHUB_TOKEN`: Personal access token with `repo` and `workflow` scopes.

### GitHub Environments

Two environments must be configured in the GitHub repository settings:

-   **`staging`:** No protection rules required.
-   **`production`:** Requires manual approval from a designated reviewer.

---

## F. How to Use

### Developer Workflow

1.  Create a new feature branch.
2.  Make code changes.
3.  Push the branch and create a pull request.
4.  The `ci-build.yml` workflow will run automatically, running tests and building Docker images.
5.  After the PR is merged, the changes will be deployed to staging automatically.

### Releasing a New Version

1.  Create a new release on GitHub with a semantic version tag (e.g., `v2.4.0`).
2.  The `cd-deploy.yml` workflow will run automatically.
3.  The new version will be deployed to staging.
4.  A manual approval will be required to deploy to production.

### Agent-Triggered Deployment

The L9 agent can trigger a deployment at any time by calling the `trigger_deployment` tool.

---

## G. Troubleshooting

-   **Deployment failures:** Check the GitHub Actions logs for detailed error messages.
-   **SSH connection issues:** Verify that the SSH keys are correctly configured and the server is accessible.
-   **Health check failures:** SSH into the server and check the Docker container logs (`docker compose logs`).
