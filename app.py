import os

from modules import create_app
from modules.config import Config

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = Config.ENVIRONMENT != "prod"

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=False
    )
