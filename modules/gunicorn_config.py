# ------------------------------------------------------
# 1) Enable INFO-level logging for both your app and Gunicorn
loglevel  = "info"

# 2) Ship Gunicorn’s error- and access-logs to stdout (Heroku captures stdout)
errorlog  = "-"
accesslog = "-"

# ------------------------------------------------------

def worker_exit(server, worker):
    """
    Called whenever a Gunicorn worker is about to exit.
    This is the safest place to flush any in‐memory buffers.
    """
    from modules.utils.queue_worker import shutdown_workers
    shutdown_workers()
