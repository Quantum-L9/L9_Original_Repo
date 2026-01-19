import os
from dataclasses import dataclass
from typing import Sequence

from fastapi import Header, HTTPException

EXECUTOR_API_KEY_L = os.environ.get("L9_EXECUTOR_API_KEY_L")
EXECUTOR_API_KEY_C = os.environ.get("L9_EXECUTOR_API_KEY_C") or os.environ.get(
    "L9_EXECUTOR_API_KEY"
)


@dataclass(frozen=True)
class CallerIdentity:
    caller_id: str
    allowed_scopes: Sequence[str]
    creator: str
    source: str


def verify_api_key(authorization: str = Header(None)) -> CallerIdentity:
    if not EXECUTOR_API_KEY_L and not EXECUTOR_API_KEY_C:
        raise HTTPException(
            status_code=500,
            detail="Executor key not configured",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    if EXECUTOR_API_KEY_L and token == EXECUTOR_API_KEY_L:
        return CallerIdentity(
            caller_id="L",
            allowed_scopes=("developer", "global", "l-private"),
            creator="L-CTO",
            source="l9-api",
        )
    if EXECUTOR_API_KEY_C and token == EXECUTOR_API_KEY_C:
        return CallerIdentity(
            caller_id="C",
            allowed_scopes=("developer", "global"),
            creator="Cursor-IDE",
            source="cursor-ide",
        )
    else:
        raise HTTPException(status_code=401, detail="Unauthorized")
