from decouple import config as env_config


class Config:
    ENVIRONMENT = env_config("ENVIRONMENT")
    MIN_SUPPORTED_VERSION = env_config("MIN_SUPPORTED_VERSION")

    # Database URIs
    PROD_URI = env_config("PROD_MONGO_URI")
    DEV_URI = env_config("DEV_MONGO_URI")
    ADMIN_URI = env_config("ADMIN_MONGO_URI")

    @classmethod
    def get_current_uri(cls):
        return cls.DEV_URI if cls.ENVIRONMENT == "dev" else cls.PROD_URI
