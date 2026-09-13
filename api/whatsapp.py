
import os
from typing import Any

from twilio.rest import Client


def load_twilio_client():
    """
    Loads Twilio client configuration from environment file for messaging setup.

    Args:
        None

    Returns:
        Twilio client object initialized with loaded credentials.

    Raises:
        RuntimeError: If configuration loading or client initialization fails.
    """
    cfg_path = "/opt/l9/twilio_config.env"
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        """
        Send a WhatsApp message using Twilio API within the WhatsApp messaging domain.

        Args:
            body: The message content to be sent.
            to: The recipient's WhatsApp number; defaults to environment variable if None.

        Returns:
            A dictionary containing the response details from the Twilio API.

        Raises:
            RuntimeError: If required environment variables are missing.
        """
        raise RuntimeError("Missing Twilio credentials")

    return Client(account_sid, auth_token)


def send_whatsapp_message(body: str, to: str | None = None) -> dict[str, Any]:
    """
    Sends a WhatsApp message using Twilio API within the messaging service.
    Args:
        body: The message content to be sent.
        to: Optional recipient phone number; defaults to environment variable if None.
    Returns:
        A dictionary containing message details and status.
    Raises:
        RuntimeError: If required environment variables are missing.
    """
    client = load_twilio_client()
    from_number = os.getenv("TWILIO_WHATSAPP_FROM")
    to_number = to or os.getenv("TWILIO_WHATSAPP_TO")
    if not from_number or not to_number:
        raise RuntimeError("Missing WhatsApp from/to numbers")

    msg = client.messages.create(
        from_=from_number,
        to=to_number,
        body=body,
    )
    return {"sid": msg.sid, "status": msg.status}


# Runtime execution trace - updated automatically on every execution
