# Replicate MCP Server

A production-ready Model Context Protocol (MCP) server for accessing Replicate's AI models. This server enables AI applications to run Replicate models through the MCP protocol, allowing for secure and controlled access with encrypted credential storage.

## Features

- Run Replicate AI models with input parameters
- List public models available on Replicate
- Get detailed information about specific models
- Securely store API credentials in MongoDB with encryption
- Integration with Twynity's auth and connection management system
- MCP Apps UI support for visualization

## Setup

### Prerequisites

1. Python 3.11 or higher
2. MongoDB instance (for connection storage)
3. Replicate API token from [replicate.com](https://replicate.com/account/api-tokens)

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

1. **run_model** - Run a Replicate model with input parameters
2. **list_models** - List all public models available on Replicate
3. **get_model_info** - Get detailed information about a specific model
4. **check_replicate_connection** - Verify connection to Replicate API

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
docker build -t replicate-mcp .
docker run -p 8000:8000 replicate-mcp
```

## License

MIT License - see [LICENSE](LICENSE) for details.