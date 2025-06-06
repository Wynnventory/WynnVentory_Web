from decouple import config as env_config


class Config:
    ENVIRONMENT = env_config("ENVIRONMENT", default="dev")
    MIN_SUPPORTED_VERSION = env_config("MIN_SUPPORTED_VERSION", default=None)

    # Database URIs
    PROD_URI = env_config("PROD_MONGO_URI", default=None)
    DEV_URI = env_config("DEV_MONGO_URI", default=None)
    ADMIN_URI = env_config("ADMIN_MONGO_URI", default=None)

    # Mod API Key
    MOD_API_KEY = env_config("MOD_API_KEY", default=None)

    @classmethod
    def get_current_uri(cls):
        return cls.DEV_URI if cls.ENVIRONMENT == "dev" else cls.PROD_URI
