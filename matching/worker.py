"""Worker in background per il calcolo dei match (geo + AI possono essere lenti).

Coda in-memory con un singolo thread daemon: serializza i job di matching,
senza introdurre nuova infrastruttura (no Celery/Redis). Le scritture sul DB
restano concorrenti con quelle delle richieste Flask: SQLite è configurato con
WAL e busy_timeout (vedi database_helper.initDB).

Limiti noti: la coda vive solo nel processo Python corrente (nessun
coordinamento cross-processo: usare un solo processo applicativo) e viene persa
al riavvio; all'avvio `engine.recomputeMissingMatches` accoda i match mancanti.

I job con lo stesso `name` non ancora avviati vengono accorpati (coalescing).
"""

import logging
import queue
import threading

logger = logging.getLogger(__name__)

_queue: "queue.Queue" = queue.Queue()
_pending: set[str] = set()
_started = False
_lock = threading.Lock()

def _runLoop():
    while True:
        name, job_fn = _queue.get()

        with _lock:
            # Da qui in poi una nuova richiesta con lo stesso nome va rieseguita.
            _pending.discard(name)

        try:
            job_fn()
        except Exception:
            logger.exception(f"[matching.worker] background job failed ({name or 'unnamed'})")
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

def enqueue(job_fn, name: str | None = None) -> bool:
    """Accoda un job (una funzione senza argomenti) per l'esecuzione in background.

    Se `name` è dato e un job con lo stesso nome è già in coda (non ancora
    partito), il nuovo job viene scartato e si ritorna False."""
    with _lock:
        if not _started:
            logger.warning("[matching.worker] enqueue() chiamato prima di startWorker(): il job resta in coda")

        if name is not None:
            if name in _pending:
                return False

            _pending.add(name)

    _queue.put((name, job_fn))

    return True
