from worker.processing_worker import ProcessingWorker

_worker: ProcessingWorker | None = None


def get_worker() -> ProcessingWorker:
    global _worker
    if _worker is None:
        _worker = ProcessingWorker()
    return _worker
