# ============================================================================
__dora_meta__ = {
    "component_name": "Vps Executor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-14T15:04:42Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "vps_executor",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /agent/health", "POST /agent/exec"],
        "datasources": ["HTTP API"],
        "memory_layers": [],
        "imported_by": ["runtime.l_tools"],
    },
}
# ============================================================================

import os
import subprocess
from typing import Literal, Optional

import httpx
import requests
import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

# Load from environment (required for server mode, optional for client imports)
EXECUTOR_KEY = os.getenv("L9_EXECUTOR_API_KEY", "")

MEMORY_HEALTH_URL = "http://127.0.0.1:8000/api/v1/memory/stats"

# RESTRICTED command whitelist (READ-ONLY operations)
ALLOWED_SHELL_PREFIXES = [
    "journalctl",
    "systemctl status",
    "ls",
    "cat",
    "tail",
    "head",
    "df",
    "du",
    "ps",
    "grep",
    "curl",
]

app = FastAPI(title="L9 CTO Agent", version="1.0")


class ShellTask(BaseModel):
    type: Literal["shell"]
    command: str
    working_dir: Optional[str] = "/opt/l9"


class MemoryHealthTask(BaseModel):
    type: Literal["memory_health"]


class CompositeTask(BaseModel):
    type: str
    command: Optional[str] = None
    working_dir: Optional[str] = "/opt/l9"


def check_auth(authorization: str = Header(...)) -> None:
    if not EXECUTOR_KEY:
        raise HTTPException(
            status_code=500, detail="L9_EXECUTOR_API_KEY not configured on server"
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = authorization.split(" ", 1)[1].strip()
    if token != EXECUTOR_KEY:
        raise HTTPException(status_code=403, detail="Invalid executor key")


def is_allowed_command(cmd: str) -> bool:
    stripped = cmd.strip()
    if not stripped:
        return False
    return any(stripped.startswith(prefix) for prefix in ALLOWED_SHELL_PREFIXES)


def run_shell(command: str, cwd: str = "/opt/l9") -> dict:
    if not is_allowed_command(command):
        raise HTTPException(
            status_code=400,
            detail=f"Command not allowed. Must start with: {', '.join(ALLOWED_SHELL_PREFIXES)}",
        )

    try:
        import shlex

        # Use shlex.split for safer command parsing (prevents shell injection)
        cmd_args = shlex.split(command)
        completed = subprocess.run(
            cmd_args,
            shell=False,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=30,  # Shorter timeout
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "Command timed out after 30s",
        }

    return {
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-2000:],
        "stderr": completed.stderr[-2000:],
    }


def memory_health() -> dict:
    try:
        resp = requests.get(
            MEMORY_HEALTH_URL,
            headers={"Authorization": f"Bearer {EXECUTOR_KEY}"},
            timeout=10,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Memory health call failed: {e}")

    return {
        "status_code": resp.status_code,
        "body": resp.text,
    }


@app.get("/agent/health")
def agent_health():
    return {"status": "ok", "role": "cto_agent", "mode": "read_only"}


@app.post("/agent/exec")
def agent_exec(task: CompositeTask, authorization: str = Header(...)):
    check_auth(authorization)

    if task.type == "shell":
        if not task.command:
            raise HTTPException(status_code=400, detail="Missing command")
        result = run_shell(task.command, task.working_dir or "/opt/l9")
        return {"mode": "shell", "command": task.command, "result": result}

    if task.type == "memory_health":
        result = memory_health()
        return {"mode": "memory_health", "result": result}

    raise HTTPException(status_code=400, detail=f"Unsupported task type: {task.type}")


# =============================================================================
# Client Function (called by runtime/l_tools.py)
# =============================================================================


async def send_mac_task(command: str, timeout: int = 30) -> dict:
    """
    Send a task to the VPS executor service.

    This is called by L's mac_agent_exec_task tool.

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds

    Returns:
        Dict with success, output, exit_code, error
    """
    executor_url = os.getenv("VPS_EXECUTOR_URL", "http://127.0.0.1:8100")
    executor_key = os.getenv("L9_EXECUTOR_API_KEY", "")

    if not executor_key:
        return {
            "success": False,
            "output": "",
            "exit_code": None,
            "error": "L9_EXECUTOR_API_KEY not configured",
        }

    try:
        async with httpx.AsyncClient(timeout=timeout + 5) as client:
            response = await client.post(
                f"{executor_url}/agent/exec",
                headers={
                    "Authorization": f"Bearer {executor_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "type": "shell",
                    "command": command,
                    "working_dir": "/opt/l9",
                },
            )

            if response.status_code == 200:
                data = response.json()
                result = data.get("result", {})
                return {
                    "success": result.get("ok", False),
                    "output": result.get("stdout", "") or result.get("stderr", ""),
                    "exit_code": result.get("exit_code"),
                    "error": result.get("stderr") if not result.get("ok") else None,
                }
            else:
                return {
                    "success": False,
                    "output": "",
                    "exit_code": None,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }

    except Exception as e:
        return {
            "success": False,
            "output": "",
            "exit_code": None,
            "error": str(e),
        }


if __name__ == "__main__":
    uvicorn.run(
        "api.vps_executor:app",
        host="127.0.0.1",
        port=8100,
        reload=False,
        log_level="info",
    )

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-009",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "endpoint",
        "http-client",
        "operations",
        "pydantic",
        "rest-api",
        "router",
    ],
    "keywords": [
        "agent",
        "allowed",
        "auth",
        "check",
        "command",
        "composite",
        "exec",
        "executor",
    ],
    "business_value": "Provides vps executor components including ShellTask, MemoryHealthTask, CompositeTask",
    "last_modified": "2026-01-14T15:04:42Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
