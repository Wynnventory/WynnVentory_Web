import os
import logging
from decouple import config

from modules import create_app
from modules.config import Config


app = create_app()

ENVIRONMENT = config("ENVIRONMENT")
Config.set_environment(ENVIRONMENT)


log = logging.getLogger('werkzeug')
# log.setLevel(logging.WARNING)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    log.info("Starting application with environment: " + Config.ENVIRONMENT)
    app.run(debug=True, host='0.0.0.0', port=port)

