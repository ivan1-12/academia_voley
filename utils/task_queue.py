from concurrent.futures import ThreadPoolExecutor
import logging

_executor = ThreadPoolExecutor(max_workers=2)


def enqueue_task(func, *args, **kwargs):
    """Encola una tarea para ejecutarse en segundo plano."""
    try:
        _executor.submit(func, *args, **kwargs)
    except Exception as e:
        logging.getLogger(__name__).exception("Error encolando tarea en segundo plano: %s", e)


def shutdown_executor():
    try:
        _executor.shutdown(wait=False)
    except Exception:
        pass
