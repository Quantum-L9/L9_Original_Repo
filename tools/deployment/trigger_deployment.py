"""
Deployment Trigger Tool for L9 Agent

This tool allows the L9 agent to autonomously trigger CI/CD deployments
by making authenticated API calls to GitHub Actions workflows.

DORA META:
- component_name: "Trigger-Deployment"
- module_version: "1.0.0"
- created_by: "Manus AI"
- created_at: "2026-01-20T00:00:00Z"
- layer: "tools"
- domain: "deployment"
- type: "agent_tool"
- status: "active"
"""

import os
from typing import Literal, Optional
from pydantic import BaseModel, Field
import httpx
from structlog import get_logger

logger = get_logger(__name__)


class DeploymentRequest(BaseModel):
    """Request model for triggering a deployment."""

    environment: Literal["staging", "production"] = Field(
        ...,
        description="Target environment for deployment",
    )
    image_tag: Optional[str] = Field(
        default="latest",
        description="Docker image tag to deploy (default: latest)",
    )
    workflow_file: str = Field(
        default="cd-deploy.yml",
        description="GitHub Actions workflow file to trigger",
    )


class DeploymentResponse(BaseModel):
    """Response model for deployment trigger."""

    success: bool = Field(..., description="Whether the deployment was triggered successfully")
    workflow_run_id: Optional[int] = Field(None, description="GitHub Actions workflow run ID")
    workflow_run_url: Optional[str] = Field(None, description="URL to view the workflow run")
    message: str = Field(..., description="Human-readable status message")


class DeploymentTrigger:
    """
    Tool for triggering GitHub Actions deployments.

    This tool enables the L9 agent to autonomously deploy new versions of itself
    and other services by triggering GitHub Actions workflows via the GitHub API.
    """

    def __init__(self):
        """Initialize the deployment trigger with GitHub credentials."""
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_repo = os.getenv("GITHUB_REPOSITORY", "cryptoxdog/L9")
        self.github_api_url = "https://api.github.com"

        if not self.github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")

        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def trigger_deployment(
        self,
        environment: Literal["staging", "production"],
        image_tag: str = "latest",
        workflow_file: str = "cd-deploy.yml",
    ) -> DeploymentResponse:
        """
        Trigger a deployment to the specified environment.

        Args:
            environment: Target environment ("staging" or "production")
            image_tag: Docker image tag to deploy (default: "latest")
            workflow_file: GitHub Actions workflow file (default: "cd-deploy.yml")

        Returns:
            DeploymentResponse with success status and workflow run details

        Raises:
            httpx.HTTPError: If the GitHub API request fails
        """
        logger.info(
            "Triggering deployment",
            environment=environment,
            image_tag=image_tag,
            workflow_file=workflow_file,
        )

        # Construct the API endpoint
        url = f"{self.github_api_url}/repos/{self.github_repo}/actions/workflows/{workflow_file}/dispatches"

        # Prepare the request payload
        payload = {
            "ref": "main",  # Branch to run the workflow from
            "inputs": {
                "environment": environment,
                "image_tag": image_tag,
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()

            # Get the workflow run ID (requires a second API call)
            workflow_run_id, workflow_run_url = await self._get_latest_workflow_run(
                workflow_file
            )

            logger.info(
                "Deployment triggered successfully",
                environment=environment,
                workflow_run_id=workflow_run_id,
            )

            return DeploymentResponse(
                success=True,
                workflow_run_id=workflow_run_id,
                workflow_run_url=workflow_run_url,
                message=f"Deployment to {environment} triggered successfully. "
                f"Workflow run ID: {workflow_run_id}",
            )

        except httpx.HTTPError as e:
            logger.error(
                "Failed to trigger deployment",
                environment=environment,
                error=str(e),
            )
            return DeploymentResponse(
                success=False,
                message=f"Failed to trigger deployment: {str(e)}",
            )

    async def _get_latest_workflow_run(
        self, workflow_file: str
    ) -> tuple[Optional[int], Optional[str]]:
        """
        Get the latest workflow run ID for the specified workflow.

        Args:
            workflow_file: GitHub Actions workflow file

        Returns:
            Tuple of (workflow_run_id, workflow_run_url)
        """
        url = f"{self.github_api_url}/repos/{self.github_repo}/actions/workflows/{workflow_file}/runs"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params={"per_page": 1},
                    timeout=30.0,
                )
                response.raise_for_status()

            data = response.json()
            if data.get("workflow_runs"):
                run = data["workflow_runs"][0]
                return run["id"], run["html_url"]

        except httpx.HTTPError as e:
            logger.warning(
                "Failed to get latest workflow run",
                workflow_file=workflow_file,
                error=str(e),
            )

        return None, None

    async def get_deployment_status(
        self, workflow_run_id: int
    ) -> dict:
        """
        Get the status of a deployment workflow run.

        Args:
            workflow_run_id: GitHub Actions workflow run ID

        Returns:
            Dictionary with workflow run status details
        """
        url = f"{self.github_api_url}/repos/{self.github_repo}/actions/runs/{workflow_run_id}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()

            data = response.json()
            return {
                "status": data["status"],  # "queued", "in_progress", "completed"
                "conclusion": data.get("conclusion"),  # "success", "failure", "cancelled", etc.
                "html_url": data["html_url"],
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
            }

        except httpx.HTTPError as e:
            logger.error(
                "Failed to get deployment status",
                workflow_run_id=workflow_run_id,
                error=str(e),
            )
            return {"status": "unknown", "error": str(e)}


# Singleton instance
_deployment_trigger: Optional[DeploymentTrigger] = None


def get_deployment_trigger() -> DeploymentTrigger:
    """Get the singleton deployment trigger instance."""
    global _deployment_trigger
    if _deployment_trigger is None:
        _deployment_trigger = DeploymentTrigger()
    return _deployment_trigger


# ============================================================================
# Agent Tool Interface
# ============================================================================

async def trigger_deployment(
    environment: Literal["staging", "production"],
    image_tag: str = "latest",
) -> DeploymentResponse:
    """
    Agent tool for triggering deployments.

    This function is exposed to the L9 agent as a tool that can be called
    to autonomously deploy new versions of the system.

    Args:
        environment: Target environment ("staging" or "production")
        image_tag: Docker image tag to deploy (default: "latest")

    Returns:
        DeploymentResponse with success status and workflow run details

    Example:
        >>> response = await trigger_deployment("staging", "v2.3.1")
        >>> print(response.message)
        "Deployment to staging triggered successfully. Workflow run ID: 12345"
    """
    trigger = get_deployment_trigger()
    return await trigger.trigger_deployment(environment, image_tag)


async def check_deployment_status(workflow_run_id: int) -> dict:
    """
    Agent tool for checking deployment status.

    Args:
        workflow_run_id: GitHub Actions workflow run ID

    Returns:
        Dictionary with workflow run status details

    Example:
        >>> status = await check_deployment_status(12345)
        >>> print(status["status"])
        "completed"
        >>> print(status["conclusion"])
        "success"
    """
    trigger = get_deployment_trigger()
    return await trigger.get_deployment_status(workflow_run_id)


# ============================================================================
# DORA FOOTER
# ============================================================================
# tags: ["agent-tool", "deployment", "ci-cd", "github-actions", "automation"]
# keywords: ["deploy", "trigger", "workflow", "agent", "autonomous"]
# last_modified: "2026-01-20T00:00:00Z"
# ============================================================================
