# Twynity API-Key MCP Template

A production-shaped [FastMCP](https://gofastmcp.com/) server template for building a Twynity MCP that needs a **single secret credential per user** — like a GitHub personal access token (`ghp_...`), a Slack token, or any one-line API key. The key is stored encrypted in MongoDB, scoped to the exact `(user_id, persona_id)` pair, and exposed over the Twynity Interconnector `api_key` category.

This is the right starting point when your MCP authenticates to an upstream service with **one token** the user pastes in — not a multi-field configuration, not an OAuth login.

## Features

- Per-user encrypted API-key storage in MongoDB (Fernet, scoped to `(user_id, persona_id)`)
- Twynity Interconnector `api_key` category: `POST /api/v1/keys` `{name, key}` + `GET /api/v1/keys`
- `GET /api/v1/keys` returns **names only — never the key** (Interconnector §11.3 security note, enforced by a test)
- `GET /api/v1/external-connection/me` connection-status endpoint
- MCP manifest (`/.well-known/mcp.json`) declaring `external_connections.api_key`
- Twynity JWT auth (audience-checked `JWTVerifier`) + `Persona-Id` scoping
- Tools resolve identity from FastMCP's verified access-token context (no re-verify of the stripped `authorization` header)
- MCP Apps UI example (the `say_hello` React app)
- Docker + Render deployment (Python 3.12 pinned)

## Setup

### Prerequisites

1. Python 3.11 or higher
2. MongoDB instance (for key storage)
3. A Twynity account-service URL + the MCP registered on Twynity (so user JWTs carry your hyphenated service ID in `aud`)

### Installation

1. Install the dependencies:

```bash
uv sync --locked
```

2. Copy `.env.example` to `.env` and configure the environment variables:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:
- `MONGODB_URI` - MongoDB connection string for storing encrypted connections
- `ENCRYPTION_KEY` - Fernet encryption key for securing credentials (generate with `uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `ACCOUNT_SERVICE_URL` - Twynity account service URL
- `ACCOUNT_SERVICE_JWKS_ENDPOINT` - JWKS endpoint for verifying JWTs
- `ACCOUNT_SERVICE_JWKS_CACHE_TTL` - Cache TTL for JWKS
- `LICENSE_KEY` - License key for usage tracking
- `LICENSE_SERVER_BASE_URL` - License server base URL
- `LICENSE_SERVER_JWKS_ENDPOINT` - JWKS endpoint for license verification
- `LICENSE_SERVER_ACTIVATION_ENDPOINT` - License activation endpoint
- `USAGE_REPORT_ENDPOINT` - Usage reporting endpoint

### Run the Server

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Tools

Replace the `say_hello` example tool with your own. A typical tool reads the user's stored key:

```python
from fastmcp.tools import ToolResult
from app.tools.connection import get_current_connection

async def my_tool(...) -> ToolResult:
    conn = await get_current_connection()  # {"id", "name", "key"}
    # call your upstream service with conn["key"]
    return ToolResult(content=[...], structured_content={...})
```

`get_current_connection()` returns the decrypted `{id, name, key}` for the verified user/persona, or raises an actionable auth error if none is set. The key is only ever decrypted inside a tool at call time — list/read routes never return it.


## Configuration

The server expects a `.env` file with the following variables:

```
# MongoDB for secure connection storage
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=twynity_mcp

# Encryption key (required)
ENCRYPTION_KEY=your_fernet_encryption_key_here

# Twynity account service details  
ACCOUNT_SERVICE_URL=https://accounts.twynity.com
ACCOUNT_SERVICE_JWKS_ENDPOINT=/oauth2/keys
ACCOUNT_SERVICE_JWKS_CACHE_TTL=300

# License service details
LICENSE_KEY=
LICENSE_SERVER_BASE_URL=https://license.twynity.com
LICENSE_SERVER_JWKS_ENDPOINT=/oauth2/keys
LICENSE_SERVER_ACTIVATION_ENDPOINT=/activate

# Usage reporting endpoint
USAGE_REPORT_ENDPOINT=https://usage.twynity.com/api/v1/report

# Public URL for the server
PUBLIC_URL=http://localhost:8000

# Environment (development, staging, production)
ENVIRONMENT=development

# Allowed origins for CORS
ALLOWED_ORIGINS=*
```

## Authentication and Security

This server uses Twynity's authentication system which requires:
1. A valid bearer JWT token
2. A `Persona-Id` header identifying the user's project/persona context

Credentials are stored securely encrypted in MongoDB, with each connection scoped to a specific user and persona pair.

## Development

### Running Tests

```bash
uv run pytest -q
```

### Code Quality

```bash
uv run ruff check app tests
```

## Deployment

### Docker

```bash
docker build -t api-key-mcp .
docker run -p 8000:8000 api-key-mcp
```

## License

MIT License - see [LICENSE](LICENSE) for details.