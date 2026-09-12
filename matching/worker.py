"""Worker in background per il calcolo dei match (geo + AI possono essere lenti).

Coda in-memory con un singolo thread daemon: serializza le scritture di match
per evitare concorrenza su SQLite, senza introdurre nuova infrastruttura (no
Celery/Redis). Limite noto: la coda vive solo nel processo Python corrente,
nessun coordinamento cross-processo se in futuro si passasse a più worker Flask.
"""

import logging
import queue
import threading

logger = logging.getLogger(__name__)

_queue: "queue.Queue" = queue.Queue()
_started = False
_lock = threading.Lock()


def _runLoop():
    while True:
        job_fn = _queue.get()

        try:
            job_fn()
        except Exception as e:
            logger.exception(f"[matching.worker] background job failed: {e}")
        finally:
            _queue.task_done()


def startWorker():
    """Avvia il thread worker una sola volta per processo."""
    global _started

    with _lock:
        if _started:
            return

        thread = threading.Thread(target=_runLoop, name="matching-worker", daemon=True)
        thread.start()
        _started = True

        logger.info("[matching.worker] background matching worker started")


def enqueue(job_fn):
    """Accoda un job (una funzione senza argomenti) per l'esecuzione in background."""
    _queue.put(job_fn)
