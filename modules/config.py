import logging
import secrets

from decouple import config as env_config

logger = logging.getLogger(__name__)


class Config:
    ENVIRONMENT = env_config("ENVIRONMENT", default="dev")
    MIN_SUPPORTED_VERSION = env_config("MIN_SUPPORTED_VERSION", default=None)

    # Database URIs
    PROD_URI = env_config("PROD_MONGO_URI", default=None)
    DEV_URI = env_config("DEV_MONGO_URI", default=None)
    ADMIN_URI = env_config("ADMIN_MONGO_URI", default=None)

    # Mod API Key
    MOD_API_KEY = env_config("MOD_API_KEY", default=None)

    # Signs the website's first-party session cookie (see routes/api/v2/auth.py)
    SECRET_KEY = env_config("SECRET_KEY", default=None)

    @classmethod
    def get_current_uri(cls):
        return cls.DEV_URI if cls.ENVIRONMENT == "dev" else cls.PROD_URI


def resolve_secret_key(environment, configured):
    """The Flask secret key to run with.

    Outside dev a missing key is a deployment error: every gunicorn worker
    would otherwise sign cookies with its own random key and the website's
    v2 calls would fail on whichever worker did not issue the cookie.
    """
    if configured:
        return configured
    if environment != "dev":
        raise RuntimeError(
            "SECRET_KEY is not set; it is required outside ENVIRONMENT=dev")
    logger.warning("SECRET_KEY is not set; using an ephemeral key for this dev process")
    return secrets.token_hex(32)
