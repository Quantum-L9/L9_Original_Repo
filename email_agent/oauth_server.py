"""
Gmail OAuth Server
==================

Tiny local HTTP server to complete OAuth flow.
Supports multi-account mode with --account flag.

Version: 2.0.0

Usage:
    python -m email_agent.oauth_server --account igor
    python -m email_agent.oauth_server --account l
    python -m email_agent.oauth_server  # Legacy mode
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Oauth Server",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-13T13:59:39Z",
    "layer": "integration",
    "domain": "email_integration",
    "module_name": "oauth_server",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

import structlog

from email_agent.config import VALID_ACCOUNTS
from email_agent.credentials import create_flow, exchange_code_for_tokens

logger = structlog.get_logger(__name__)

# Default port
DEFAULT_PORT = 8080

# Module-level state (set by CLI)
CURRENT_ACCOUNT: Optional[str] = None
CURRENT_PORT: int = DEFAULT_PORT


class OAuthHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth flow."""

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/oauth/start":
            self.handle_start()
        elif path == "/oauth/callback":
            self.handle_callback(parsed_path.query)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def handle_start(self):
        """Start OAuth flow - redirect to Google consent."""
        global CURRENT_ACCOUNT, CURRENT_PORT
        try:
            redirect_uri = f"http://localhost:{CURRENT_PORT}/oauth/callback"
            flow = create_flow(redirect_uri=redirect_uri, account=CURRENT_ACCOUNT)

            if not flow:
                self.send_response(500)
                self.end_headers()
                account_label = CURRENT_ACCOUNT or "legacy"
                self.wfile.write(
                    f"Failed to create OAuth flow for account '{account_label}'. "
                    f"Check client_secret.json exists.".encode()
                )
                return

            # Get authorization URL
            auth_url, _ = flow.authorization_url(
                access_type="offline", include_granted_scopes="true"
            )

            # Redirect to Google
            self.send_response(302)
            self.send_header("Location", auth_url)
            self.end_headers()

            logger.info(f"Redirecting to: {auth_url}")

        except Exception as e:
            logger.error(f"Error starting OAuth flow: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode())

    def handle_callback(self, query_string: str):
        """Handle OAuth callback - exchange code for tokens."""
        global CURRENT_ACCOUNT, CURRENT_PORT
        try:
            params = parse_qs(query_string)
            code = params.get("code", [None])[0]
            error = params.get("error", [None])[0]

            if error:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"OAuth error: {error}".encode())
                logger.error(f"OAuth error: {error}")
                return

            if not code:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing authorization code")
                return

            # Exchange code for tokens
            redirect_uri = f"http://localhost:{CURRENT_PORT}/oauth/callback"
            credentials = exchange_code_for_tokens(
                code, redirect_uri, account=CURRENT_ACCOUNT
            )

            if credentials:
                # Determine account info for display
                if CURRENT_ACCOUNT:
                    from email_agent.config import get_account_config

                    config = get_account_config(CURRENT_ACCOUNT)
                    account_email = config.email
                    tokens_path = str(config.tokens_file)
                else:
                    from email_agent.config import GMAIL_ACCOUNT, TOKENS_FILE

                    account_email = GMAIL_ACCOUNT
                    tokens_path = str(TOKENS_FILE)

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"""
                    <html>
                    <head><title>Gmail OAuth Complete</title></head>
                    <body>
                        <h1>✅ Gmail OAuth completed successfully!</h1>
                        <p><strong>Account:</strong> {CURRENT_ACCOUNT or "legacy"}</p>
                        <p><strong>Email:</strong> {account_email}</p>
                        <p><strong>Tokens saved to:</strong> {tokens_path}</p>
                        <p>You can close this window.</p>
                    </body>
                    </html>
                """.encode("utf-8"))

                logger.info(
                    f"✅ OAuth completed for account: {CURRENT_ACCOUNT or 'legacy'}"
                )
                logger.info(f"   Email: {account_email}")
                logger.info(f"   Tokens: {tokens_path}")
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Failed to exchange code for tokens")

        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode())

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.debug(f"{self.address_string()} - {format % args}")


def main():
    """Run OAuth server with CLI args."""
    global CURRENT_ACCOUNT, CURRENT_PORT

    parser = argparse.ArgumentParser(
        description="Gmail OAuth Server - Authenticate Gmail accounts for L9"
    )
    parser.add_argument(
        "--account",
        choices=VALID_ACCOUNTS,
        help=f"Account to authenticate ({', '.join(VALID_ACCOUNTS)}). "
        "If not specified, uses legacy mode.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to run server on (default: {DEFAULT_PORT})",
    )
    args = parser.parse_args()

    CURRENT_ACCOUNT = args.account
    CURRENT_PORT = args.port

    # Display account info
    print("\n" + "=" * 60)
    print("Gmail OAuth Server")
    print("=" * 60)

    if CURRENT_ACCOUNT:
        from email_agent.config import get_account_config

        config = get_account_config(CURRENT_ACCOUNT)
        print(f"Account:       {CURRENT_ACCOUNT}")
        print(f"Email:         {config.email}")
        print(f"Client Secret: {config.client_secret_file}")
        print(f"Tokens:        {config.tokens_file}")
    else:
        from email_agent.config import (CLIENT_SECRET_FILE, GMAIL_ACCOUNT,
                                        TOKENS_FILE)

        print("Mode:          LEGACY (no account specified)")
        print(f"Email:         {GMAIL_ACCOUNT}")
        print(f"Client Secret: {CLIENT_SECRET_FILE}")
        print(f"Tokens:        {TOKENS_FILE}")

    print("=" * 60)
    print(f"\n🌐 Server: http://localhost:{CURRENT_PORT}")
    print(f"📋 Open:   http://localhost:{CURRENT_PORT}/oauth/start")
    print("\nPress Ctrl+C to stop\n")

    server_address = ("", CURRENT_PORT)
    httpd = HTTPServer(server_address, OAuthHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        httpd.shutdown()


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "EMA-INTE-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "auth",
        "cli",
        "debugging",
        "email-integration",
        "handler",
        "integration",
        "logging",
        "messaging",
        "security",
    ],
    "keywords": [
        "account",
        "auth",
        "callback",
        "handle",
        "handler",
        "log",
        "mode",
        "oauth",
    ],
    "business_value": "Implements OAuthHandler for oauth server functionality",
    "last_modified": "2026-01-13T13:59:39Z",
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
