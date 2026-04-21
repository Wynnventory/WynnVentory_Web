# Configuration

**Source:** `modules/config.py`

## Overview

Configuration is managed by the `Config` class using `python-decouple`, which reads from environment variables (with optional `.env` file support in development).

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `"dev"` | Deployment environment. Set to `"prod"` for production. Controls which MongoDB URI is used and whether Flask debug mode is enabled. |
| `MIN_SUPPORTED_VERSION` | No | `None` | Minimum mod version accepted by the server. Submissions from older versions are rejected. Format: `"X.Y.Z"` (e.g., `"1.2.0"`). When `None`, all versions are accepted. |
| `PROD_MONGO_URI` | Yes (prod) | `None` | MongoDB connection string for the production database. Must include the database name in the URI. |
| `DEV_MONGO_URI` | Yes (dev) | `None` | MongoDB connection string for the development database. |
| `ADMIN_MONGO_URI` | Yes | `None` | MongoDB connection string for the admin database (API keys and usage). |
| `MOD_API_KEY` | Yes | `None` | SHA-256 hash of the mod's embedded API key. Used to identify mod key requests. |
| `PORT` | No | `5000` | Port for the Flask development server. In production, Gunicorn binds to `$PORT` automatically (Heroku sets this). |

## Config Class

```python
class Config:
    ENVIRONMENT = env_config("ENVIRONMENT", default="dev")
    MIN_SUPPORTED_VERSION = env_config("MIN_SUPPORTED_VERSION", default=None)
    PROD_URI = env_config("PROD_MONGO_URI", default=None)
    DEV_URI = env_config("DEV_MONGO_URI", default=None)
    ADMIN_URI = env_config("ADMIN_MONGO_URI", default=None)
    MOD_API_KEY = env_config("MOD_API_KEY", default=None)

    @classmethod
    def get_current_uri(cls):
        return cls.DEV_URI if cls.ENVIRONMENT == "dev" else cls.PROD_URI
```

## Database URI Selection

`Config.get_current_uri()` returns:
- `DEV_URI` when `ENVIRONMENT == "dev"` (default)
- `PROD_URI` when `ENVIRONMENT == "prod"`

The admin database always uses `ADMIN_URI` regardless of environment.

## Usage in the Application

| Component | Config Values Used |
|-----------|-------------------|
| `db.py` | `ADMIN_URI`, `get_current_uri()` |
| `auth.py` | `MOD_API_KEY` |
| `market_service.py` | `MIN_SUPPORTED_VERSION` |
| `base_pool_service.py` | `MIN_SUPPORTED_VERSION` |
| `raidpool_service.py` | `MIN_SUPPORTED_VERSION` |
| `app.py` | `ENVIRONMENT`, `PORT` |
| `__init__.py` | `ENVIRONMENT`, `MIN_SUPPORTED_VERSION` (logging) |
