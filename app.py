import os
import logging
from modules import create_app
from flask_cors import CORS

app = create_app()

CORS(app, resources={r"/api/*": {"origins": "https://www.wynnventory.com"}})

log = logging.getLogger('werkzeug')
# log.setLevel(logging.WARNING)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)