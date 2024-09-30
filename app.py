import os
import logging
from modules import create_app

app = create_app()

log = logging.getLogger('werkzeug')
# log.setLevel(logging.WARNING)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)