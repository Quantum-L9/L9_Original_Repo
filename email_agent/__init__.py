"""L9 Email Agent - Gmail API integration."""

from email_agent.client import execute_email_task
from email_agent.credentials import (
    create_flow,
    exchange_code_for_tokens,
    load_client_secrets,
    load_tokens,
    save_tokens,
)
from email_agent.gmail_client import GmailClient
from email_agent.triage import run_daily_digest, summarize_inbox

__all__ = [
    "GmailClient",
    "create_flow",
    "exchange_code_for_tokens",
    "execute_email_task",
    "load_client_secrets",
    "load_tokens",
    "run_daily_digest",
    "save_tokens",
    "summarize_inbox",
]
