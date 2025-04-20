import atexit
import os

from modules import create_app
from modules.config import Config
from modules.utils.queue_worker import shutdown_workers

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = Config.ENVIRONMENT != "prod"
    app.logger.info(f"Starting in '{Config.ENVIRONMENT}' mode with min version '{Config.MIN_SUPPORTED_VERSION}')")

    atexit.register(shutdown_workers)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug
    )
