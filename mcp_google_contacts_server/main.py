"""
MCP Google Contacts Server built on FastMCP 2.x.

Two deployment shapes are supported:

* **Local / stdio** – unchanged behaviour: credentials come from
  ``credentials.json`` or ``GOOGLE_*`` env vars and the server speaks stdio
  to a local MCP client.
* **Remote / HTTP (e.g. Prefect Horizon)** – the server exposes an HTTP
  (streamable-http) transport and is protected by Google OAuth via
  :class:`fastmcp.server.auth.providers.google.GoogleProvider`. Users sign
  in with their Google account before any tool is callable. The People API
  itself is still reached with the server's own refresh-token credentials
  (usually the deployer's Google account).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from mcp_google_contacts_server.config import config
from mcp_google_contacts_server.tools import init_service, register_tools


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP Google Contacts Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http", "sse"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport protocol to use (default: stdio, or $MCP_TRANSPORT)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host for HTTP transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", os.environ.get("PORT", "8000"))),
        help="Port for HTTP transport (default: 8000 / $PORT)",
    )
    parser.add_argument(
        "--client-id",
        help="Google OAuth client ID (overrides environment variable)",
    )
    parser.add_argument(
        "--client-secret",
        help="Google OAuth client secret (overrides environment variable)",
    )
    parser.add_argument(
        "--refresh-token",
        help="Google OAuth refresh token (overrides environment variable)",
    )
    parser.add_argument(
        "--credentials-file",
        help="Path to Google OAuth credentials.json file",
    )
    parser.add_argument(
        "--oauth",
        action="store_true",
        default=config.oauth_enabled,
        help=(
            "Protect the MCP server with Google OAuth (GoogleProvider). "
            "Also enabled via MCP_OAUTH_ENABLED=1."
        ),
    )
    parser.add_argument(
        "--oauth-base-url",
        default=config.oauth_base_url,
        help="Public base URL of this server (required with --oauth).",
    )
    return parser.parse_args()


def _build_auth_provider():
    """Instantiate the Google OAuth provider that gates access to the server."""
    from fastmcp.server.auth.providers.google import GoogleProvider

    client_id = os.environ.get("GOOGLE_CLIENT_ID") or config.google_client_id
    client_secret = (
        os.environ.get("GOOGLE_CLIENT_SECRET") or config.google_client_secret
    )
    if not client_id or not client_secret:
        raise RuntimeError(
            "Google OAuth gating requires GOOGLE_CLIENT_ID and "
            "GOOGLE_CLIENT_SECRET to be set."
        )
    if not config.oauth_base_url:
        raise RuntimeError(
            "Google OAuth gating requires MCP_OAUTH_BASE_URL (or "
            "--oauth-base-url) to be set to the public URL of this server."
        )

    # Always request the People-API scopes alongside the identity scopes so
    # the consent screen makes it clear what the server will access.
    required_scopes = list(dict.fromkeys(config.oauth_required_scopes + config.scopes))

    kwargs = dict(
        client_id=client_id,
        client_secret=client_secret,
        base_url=config.oauth_base_url,
        redirect_path=config.oauth_redirect_path,
        required_scopes=required_scopes,
    )
    if config.oauth_jwt_signing_key:
        kwargs["jwt_signing_key"] = config.oauth_jwt_signing_key

    return GoogleProvider(**kwargs)


def _install_email_allow_list(mcp: FastMCP) -> None:
    """Reject tool calls from Google accounts that are not in the allow-list."""
    if not config.oauth_allowed_emails:
        return

    from fastmcp.server.dependencies import get_access_token
    from fastmcp.server.middleware import Middleware, MiddlewareContext

    allowed = {e.lower() for e in config.oauth_allowed_emails}

    class EmailAllowListMiddleware(Middleware):
        async def on_call_tool(self, context: MiddlewareContext, call_next):
            token = get_access_token()
            email = None
            if token is not None:
                email = (token.claims or {}).get("email")
            if not email or email.lower() not in allowed:
                raise PermissionError(
                    "This Google account is not allowed to use this MCP server."
                )
            return await call_next(context)

    mcp.add_middleware(EmailAllowListMiddleware())


def main() -> None:
    print("Starting Google Contacts MCP Server...", file=sys.stderr)

    args = parse_args()

    if args.client_id:
        os.environ["GOOGLE_CLIENT_ID"] = args.client_id
        config.google_client_id = args.client_id
    if args.client_secret:
        os.environ["GOOGLE_CLIENT_SECRET"] = args.client_secret
        config.google_client_secret = args.client_secret
    if args.refresh_token:
        os.environ["GOOGLE_REFRESH_TOKEN"] = args.refresh_token
        config.google_refresh_token = args.refresh_token
    if args.oauth_base_url:
        config.oauth_base_url = args.oauth_base_url

    if args.credentials_file:
        credentials_path = Path(args.credentials_file)
        if credentials_path.exists():
            config.credentials_paths.insert(0, credentials_path)
            print(f"Using credentials file: {credentials_path}", file=sys.stderr)
        else:
            print(
                f"Warning: credentials file {credentials_path} not found",
                file=sys.stderr,
            )

    auth_provider = None
    if args.oauth:
        print(
            "Google OAuth gating enabled (GoogleProvider).", file=sys.stderr
        )
        auth_provider = _build_auth_provider()

    mcp = FastMCP(name="google-contacts", auth=auth_provider)

    register_tools(mcp)
    _install_email_allow_list(mcp)

    service = init_service()
    if not service:
        print(
            "Warning: No valid Google credentials found for the People API. "
            "Set GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET/GOOGLE_REFRESH_TOKEN or "
            "provide --credentials-file.",
            file=sys.stderr,
        )

    transport = args.transport
    if transport == "stdio":
        print("Running with stdio transport", file=sys.stderr)
        mcp.run(transport="stdio")
    else:
        transport_name = "http" if transport == "http" else transport
        print(
            f"Running with {transport_name} transport on {args.host}:{args.port}",
            file=sys.stderr,
        )
        mcp.run(transport=transport_name, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
