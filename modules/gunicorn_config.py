def worker_exit(server, worker):
    """
    Called whenever a Gunicorn worker is about to exit.
    This is the safest place to flush any in‐memory buffers.
    """
    from modules.utils.queue_worker import shutdown_workers
    shutdown_workers()
