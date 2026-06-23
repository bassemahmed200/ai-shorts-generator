import os
import threading
from typing import Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, Future

_jobs: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

# Thread pool: up to 10 jobs running at the same time
# Each job = 1 video being processed
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="job")
_futures: Dict[str, Future] = {}

def create_job(job_id: str):
    with _lock:
        _jobs[job_id] = {
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None
        }

def update_job(job_id: str, status: str, progress: float, result: Any = None):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = status
            _jobs[job_id]["progress"] = progress
            if status == "failed":
                _jobs[job_id]["error"] = result
            elif status == "done":
                _jobs[job_id]["result"] = result

def get_job(job_id: str) -> Dict[str, Any]:
    with _lock:
        return _jobs.get(job_id)

def delete_job(job_id: str):
    with _lock:
        if job_id in _jobs:
            del _jobs[job_id]
        if job_id in _futures:
            _futures.pop(job_id, None)

def submit_job(job_id: str, func: Callable, **kwargs):
    """Submit a job to the thread pool. job_id is passed via kwargs to func."""
    kwargs["job_id"] = job_id
    future = _executor.submit(func, **kwargs)
    with _lock:
        _futures[job_id] = future

def get_active_count() -> int:
    """How many jobs are currently running."""
    with _lock:
        return sum(1 for f in _futures.values() if not f.done())

def get_queue_size() -> int:
    """How many jobs are waiting in queue."""
    with _lock:
        return _executor._max_workers - get_active_count()
