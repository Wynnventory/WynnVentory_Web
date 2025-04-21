import os

from decouple import config as env_config
ENVIRONMENT = env_config("ENVIRONMENT")
MIN_SUPPORTED_VERSION = env_config("MIN_SUPPORTED_VERSION")

from modules.config import Config
Config.ENVIRONMENT = ENVIRONMENT
Config.MIN_SUPPORTED_VERSION = MIN_SUPPORTED_VERSION

from modules import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = Config.ENVIRONMENT != "prod"

    app.logger.warning(
        "Starting in '%s' mode with min version '%s'",
        Config.ENVIRONMENT,
        Config.MIN_SUPPORTED_VERSION
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=False
    )
