import threading

from matching import worker


def test_start_worker_is_idempotent_and_runs_jobs_in_order():
    worker.startWorker()
    worker.startWorker()

    threads = [t for t in threading.enumerate() if t.name == "matching-worker"]
    assert len(threads) == 1

    results = []
    for i in range(3):
        worker.enqueue(lambda i=i: results.append(i))
    worker._queue.join()

    assert results == [0, 1, 2]


def test_failing_job_does_not_stop_the_worker():
    worker.startWorker()
    results = []

    worker.enqueue(lambda: 1 / 0, name="boom")
    worker.enqueue(lambda: results.append("ok"))
    worker._queue.join()

    assert results == ["ok"]


def test_jobs_with_same_name_are_coalesced_while_pending():
    worker.startWorker()
    gate = threading.Event()
    results = []

    worker.enqueue(gate.wait, name="blocker")
    # Il blocker sta girando: il primo "same" viene accodato, il secondo scartato.
    while "blocker" in worker._pending:
        pass

    assert worker.enqueue(lambda: results.append(1), name="same") is True
    assert worker.enqueue(lambda: results.append(2), name="same") is False

    gate.set()
    worker._queue.join()

    assert results == [1]
    assert worker.enqueue(lambda: results.append(3), name="same") is True
    worker._queue.join()
    assert results == [1, 3]
