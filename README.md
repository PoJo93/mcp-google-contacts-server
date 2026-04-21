[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/rayanzaki-mcp-google-contacts-server-badge.png)](https://mseep.ai/app/rayanzaki-mcp-google-contacts-server)

# MCP Google Contacts Server

A [FastMCP 2.x](https://gofastmcp.com/) server that exposes Google Contacts to
MCP clients such as Claude. It can run as a local **stdio** server or as a
remote **HTTP** server protected by **Google OAuth** (ready to be deployed to
[Prefect Horizon](https://www.prefect.io/horizon) – or any other MCP host).

## Features

- List, get, create, update, delete contacts
- Search contacts, Workspace directory, "Other contacts"
- **New:** `update_contact_photo` – give the AI a URL, the server downloads the
  image, base64-encodes it and PATCHes `people.updateContactPhoto`
- Optional Google OAuth gate: users must sign in with their Google account
  before any tool can be called
- Optional e-mail allow-list (`MCP_OAUTH_ALLOWED_EMAILS`)

## Installation

Requires Python 3.12+.

```bash
pip install .
# or
uv sync
```

## Running

### Local (stdio)

The classic setup – credentials come from a `credentials.json` file or from
`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REFRESH_TOKEN`
environment variables. No OAuth gate.

```bash
mcp-google-contacts
```

### Remote / Prefect (HTTP + Google OAuth)

Two roles:

1. **Server credentials** used to call the Google People API on your behalf –
   `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`.
   Obtain the refresh token once by running the server locally with stdio and
   going through the browser flow. Store the three values as Prefect secrets.
2. **OAuth gate** used to authenticate *the caller* of the MCP server with
   their Google account via FastMCP's
   [`GoogleProvider`](https://gofastmcp.com/integrations/google).

Minimum env vars for a Prefect Horizon deployment:

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth Web client ID (Cloud Console) |
| `GOOGLE_CLIENT_SECRET` | OAuth Web client secret |
| `GOOGLE_REFRESH_TOKEN` | Refresh token authorising the People API calls |
| `MCP_OAUTH_ENABLED` | `1` to turn the OAuth gate on |
| `MCP_OAUTH_BASE_URL` | Public URL Prefect assigns, e.g. `https://contacts-xyz.horizon.prefect.dev` |
| `MCP_OAUTH_REDIRECT_PATH` | Defaults to `/auth/callback` – add the same to the OAuth client's *Authorized redirect URIs* |
| `MCP_OAUTH_ALLOWED_EMAILS` | Optional comma-separated allow-list |
| `MCP_OAUTH_JWT_SIGNING_KEY` | Optional persistent HMAC key so FastMCP-issued JWTs survive restarts |
| `MCP_TRANSPORT` | Set to `http` (or `streamable-http`) for remote use |
| `PORT` | Prefect sets this – picked up automatically |

Run command for a Prefect container:

```bash
mcp-google-contacts --transport http --oauth
```

or equivalently just:

```bash
MCP_TRANSPORT=http MCP_OAUTH_ENABLED=1 mcp-google-contacts
```

### Google Cloud Console setup

1. Enable the **People API** in your project.
2. Create an OAuth 2.0 **Web application** client.
3. Under *Authorized redirect URIs* add `${MCP_OAUTH_BASE_URL}/auth/callback`.
4. Grant the scopes `openid`, `userinfo.email`, `auth/contacts`, and
   `auth/directory.readonly` on the consent screen.

## Tools

| Tool | Description |
|------|-------------|
| `list_contacts` | List contacts, optional name filter |
| `get_contact` | Get a contact by resource name or email |
| `create_contact` | Create a new contact |
| `update_contact` | Update an existing contact |
| `delete_contact` | Delete a contact |
| `search_contacts` | Local fuzzy search across name / email / phone |
| `list_workspace_users` | List Google Workspace directory users |
| `search_directory` | Search the Workspace directory |
| `get_other_contacts` | People from the "Other contacts" section |
| `update_contact_photo` | **New** – set a contact's photo from a URL |

### `update_contact_photo`

```python
update_contact_photo(
    resource_name="people/c12345678901234567",
    photo_url="https://example.com/jane.jpg",
    # target_size=720,  # optional, default 720 (Google's recommendation)
)
```

The server:

1. Downloads the URL (up to 25 MB raw, any format Pillow can decode).
2. Honours EXIF orientation, flattens transparency onto white.
3. **Center-crops to a 1:1 square** – Google displays contact photos as
   circles, so non-square input would be ugly.
4. **Resizes to 720×720 px** (Google's recommended profile photo size;
   minimum is 250 px). Configurable via `target_size` argument or
   `MCP_CONTACT_PHOTO_SIZE` env var. Source images smaller than the target
   are kept at their original size (no upscaling).
5. JPEG-encodes with progressive quality fallback so the payload stays
   under Google's 5 MB upload cap.
6. Base64-encodes and calls
   `PATCH https://people.googleapis.com/v1/{resourceName}:updateContactPhoto`
   ([docs](https://developers.google.com/people/api/rest/v1/people/updateContactPhoto)).

## MCP client configuration (local)

```json
{
  "mcpServers": {
    "google-contacts-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-google-contacts-server",
        "run",
        "mcp-google-contacts"
      ]
    }
  }
}
```

For a remote Prefect-hosted server your MCP client simply points at
`${MCP_OAUTH_BASE_URL}/mcp` (or the URL Prefect shows) and negotiates OAuth on
the first connection.

## License

MIT – see LICENSE.
