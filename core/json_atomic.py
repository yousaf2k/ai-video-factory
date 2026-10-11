"""
Atomic, lock-protected JSON read-modify-write utilities.

Every JSON file that multiple writers may touch concurrently (queue worker
threads, FastAPI request handlers, CLI pipeline, spawned subprocesses) must
go through these helpers. The contract is always:

    acquire lock -> read the LATEST bytes from disk -> apply mutation ->
    write atomically (temp file + os.replace) -> release lock

An in-memory snapshot of a file must never be written back wholesale,
because another writer may have updated the file after the snapshot was
taken (last-writer-wins data loss, e.g. two parallel image generations
overwriting each other's shot updates in shots.json).
"""
import json
import os
import random
import threading
import time

from core.logger_config import get_logger

logger = get_logger(__name__)

# Process-wide registry: lock path -> (threading.RLock, {thread_ident: depth})
_thread_locks: dict = {}
_registry_guard = threading.Lock()

_REPLACE_RETRIES = 6
_REPLACE_RETRY_DELAY = 0.1


def _get_thread_lock(lock_path: str) -> threading.RLock:
    with _registry_guard:
        entry = _thread_locks.get(lock_path)
        if entry is None:
            entry = (threading.RLock(), {})
            _thread_locks[lock_path] = entry
        return entry[0]


def _get_lock_depths(lock_path: str) -> dict:
    with _registry_guard:
        return _thread_locks.setdefault(lock_path, (threading.RLock(), {}))[1]


class file_lock:
    """
    Re-entrant, cross-process lock for a file or resource.

    - Intra-process: threading.RLock keyed by lock path (so nested acquisition
      in the same thread never deadlocks).
    - Cross-process: atomic directory creation at ``lock_path`` (works on
      Windows and POSIX). Directory locks older than ``stale_after`` seconds
      are treated as stale (crashed writer) and removed.

    Usage:
        with file_lock("/path/to/project/.project_lock"):
            data = read latest from disk
            mutate(data)
            atomic_write_json(...)
    """

    def __init__(self, lock_path: str, timeout: float = 30.0, stale_after: float = 120.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self.stale_after = stale_after
        self._depth_key = threading.get_ident()

    def __enter__(self):
        rlock = _get_thread_lock(self.lock_path)
        acquired = rlock.acquire(timeout=self.timeout)
        if not acquired:
            raise TimeoutError(f"Could not acquire thread lock for {self.lock_path} after {self.timeout}s")
        depths = _get_lock_depths(self.lock_path)
        if depths.get(self._depth_key, 0) > 0:
            # Nested acquisition in the same thread: nothing more to do.
            depths[self._depth_key] += 1
            return self

        lock_dir = self.lock_path
        parent = os.path.dirname(lock_dir)
        if parent:
            os.makedirs(parent, exist_ok=True)

        start_time = time.time()
        acquired_fs = False
        try:
            while time.time() - start_time < self.timeout:
                try:
                    os.mkdir(lock_dir)
                    acquired_fs = True
                    break
                except FileExistsError:
                    self._remove_stale_lock()
                    time.sleep(0.05)
                except PermissionError:
                    # Transient on Windows while another process removes the dir
                    time.sleep(0.05)

            if not acquired_fs:
                raise TimeoutError(f"Could not acquire file lock {lock_dir} after {self.timeout}s")

            depths[self._depth_key] = 1
        except Exception:
            rlock.release()
            raise
        return self

    def __exit__(self, exc_type, exc, tb):
        depths = _get_lock_depths(self.lock_path)
        depths[self._depth_key] = max(0, depths.get(self._depth_key, 1) - 1)
        is_outermost = depths[self._depth_key] == 0
        if is_outermost:
            depths.pop(self._depth_key, None)
            try:
                os.rmdir(self.lock_path)
            except FileNotFoundError:
                pass
            except OSError as e:
                logger.warning(f"Failed to release lock {self.lock_path}: {e}")
        rlock = _get_thread_lock(self.lock_path)
        rlock.release()
        return False

    def _remove_stale_lock(self):
        """Remove the lock directory if it is older than stale_after seconds."""
        try:
            mtime = os.path.getmtime(self.lock_path)
            if time.time() - mtime > self.stale_after:
                logger.warning(f"Removing stale lock {self.lock_path} (age > {self.stale_after}s)")
                os.rmdir(self.lock_path)
        except FileNotFoundError:
            pass
        except OSError:
            # Lock was re-created or is busy; retry on the next loop iteration.
            pass


def read_json(path: str, default=None):
    """Read and parse a JSON file. Returns ``default`` if missing or corrupt."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Malformed JSON in {path}: {e}")
        return default
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return default


def atomic_write_json(path: str, data, indent: int = 2, encoder_kwargs: dict = None) -> None:
    """
    Write JSON atomically: serialize to a temp file in the same directory,
    flush + fsync, then os.replace() over the target. Readers never observe a
    torn/partial file, and a crash never leaves a truncated JSON behind.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    kwargs = dict(ensure_ascii=False)
    if encoder_kwargs:
        kwargs.update(encoder_kwargs)

    tmp_path = os.path.join(
        directory, f".{os.path.basename(path)}.tmp-{os.getpid()}-{random.randint(1000, 9999)}"
    )
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, **kwargs)
            f.flush()
            os.fsync(f.fileno())

        last_err = None
        for attempt in range(_REPLACE_RETRIES):
            try:
                os.replace(tmp_path, path)
                return
            except PermissionError as e:
                # Windows: a concurrent reader may briefly hold the target open.
                last_err = e
                time.sleep(_REPLACE_RETRY_DELAY * (attempt + 1))
        raise last_err
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


def update_json(path: str, modify_func, default=None, lock_path: str = None, timeout: float = 30.0):
    """
    Locked read-modify-write of a JSON file.

    Acquires the lock, re-reads the file from disk (never a cached snapshot),
    applies ``modify_func(data)`` (mutate the parsed object in place, or
    return a replacement), and writes the result atomically.

    Args:
        path: JSON file path.
        modify_func: callable receiving the parsed data (or ``default`` if the
            file is missing/corrupt). May mutate in place and/or return the
            new value; the returned value (if not None) is what gets written.
        default: value handed to modify_func when the file doesn't exist.
        lock_path: lock resource (defaults to ``<path>.lock`` next to the file).
            Pass a shared project-level lock path to transact several files
            (e.g. shots.json + meta.json) under one lock.
        timeout: seconds to wait for the lock.

    Returns:
        The data as written (or None when modify_func returned None and the
        caller signalled "no write" by returning the sentinel NO_WRITE).
    """
    if lock_path is None:
        lock_path = path + ".lock"
    with file_lock(lock_path, timeout=timeout):
        data = read_json(path, default=default)
        result = modify_func(data)
        if result is NO_WRITE:
            return data
        if result is not None:
            data = result
        atomic_write_json(path, data)
        return data


class _NoWrite:
    """Sentinel for update_json: skip the write, just release the lock."""


NO_WRITE = _NoWrite()
