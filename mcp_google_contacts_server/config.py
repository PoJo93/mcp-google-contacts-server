import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field


class ContactsConfig(BaseModel):
    """Configuration for Google Contacts integration."""

    google_client_id: Optional[str] = Field(
        default=None,
        description="Google OAuth client ID",
    )
    google_client_secret: Optional[str] = Field(
        default=None,
        description="Google OAuth client secret",
    )
    google_refresh_token: Optional[str] = Field(
        default=None,
        description="Google OAuth refresh token used by the server to call the People API",
    )
    credentials_paths: List[Path] = Field(
        default_factory=list,
        description="Paths to search for credentials.json file",
    )
    token_path: Path = Field(
        default=Path.home() / ".config" / "google-contacts-mcp" / "token.json",
        description="Path to store the token file",
    )
    default_max_results: int = Field(
        default=100,
        description="Default maximum number of results to return",
    )
    scopes: List[str] = Field(
        default=[
            "https://www.googleapis.com/auth/contacts",
            "https://www.googleapis.com/auth/directory.readonly",
        ],
        description="OAuth scopes required for the People API calls",
    )

    # --- OAuth-gated remote deployment (e.g. Prefect Horizon) ---
    oauth_enabled: bool = Field(
        default=False,
        description=(
            "Enable the FastMCP GoogleProvider that protects the MCP server "
            "itself. Clients must sign in with Google before any tool call."
        ),
    )
    oauth_base_url: Optional[str] = Field(
        default=None,
        description=(
            "Public base URL where the MCP server is reachable "
            "(e.g. https://contacts.my-prefect-horizon.app). Required when "
            "oauth_enabled=True."
        ),
    )
    oauth_redirect_path: str = Field(
        default="/auth/callback",
        description="Path that Google will redirect to after a successful login.",
    )
    oauth_required_scopes: List[str] = Field(
        default=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        description="Minimum Google OAuth scopes the signed-in user must grant.",
    )
    oauth_allowed_emails: List[str] = Field(
        default_factory=list,
        description=(
            "Optional allow-list of Google account e-mails permitted to use "
            "the server. Empty means: allow every signed-in Google user."
        ),
    )
    oauth_jwt_signing_key: Optional[str] = Field(
        default=None,
        description=(
            "Persistent HMAC signing key for FastMCP-issued JWTs. Recommended "
            "when running behind Prefect so tokens survive restarts."
        ),
    )


def _split_env_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def load_config() -> ContactsConfig:
    """Load configuration from environment variables and defaults."""
    default_paths = [
        Path.home() / ".config" / "google" / "credentials.json",
        Path.home() / "google_credentials.json",
        Path(__file__).parent / "credentials.json",
    ]

    token_dir = Path.home() / ".config" / "google-contacts-mcp"
    token_dir.mkdir(parents=True, exist_ok=True)

    oauth_enabled = os.environ.get("MCP_OAUTH_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    return ContactsConfig(
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        google_refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN"),
        credentials_paths=default_paths,
        token_path=token_dir / "token.json",
        oauth_enabled=oauth_enabled,
        oauth_base_url=os.environ.get("MCP_OAUTH_BASE_URL"),
        oauth_redirect_path=os.environ.get(
            "MCP_OAUTH_REDIRECT_PATH", "/auth/callback"
        ),
        oauth_allowed_emails=_split_env_list(
            os.environ.get("MCP_OAUTH_ALLOWED_EMAILS")
        ),
        oauth_jwt_signing_key=os.environ.get("MCP_OAUTH_JWT_SIGNING_KEY"),
    )


# Global configuration instance
config = load_config()
