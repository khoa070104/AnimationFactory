"""Cross-process project lock shared by the CLI, the MCP server and the UI: two writers can never interleave check-and-write.
A lock is an exclusively created file (works on Windows and POSIX); inside one process a thread lock comes first, and the same thread may re-enter.
shortcut: stale locks are detected by file age only (pids are unreliable behind the Windows Store python launcher), so `stale` must exceed the longest critical section."""
import contextlib
import os
import threading
import time
from pathlib import Path

_local = threading.local()
_tlocks = {}
_guard = threading.Lock()


class LockBusy(Exception):
    pass


@contextlib.contextmanager
def lock(proj, name="project", timeout=30.0, stale=120.0):
    f = Path(proj) / ".locks" / f"{name}.lock"
    f.parent.mkdir(parents=True, exist_ok=True)
    key = str(f)
    held = getattr(_local, "held", None)
    if held is None:
        held = _local.held = {}
    if held.get(key):                                           # re-entry by the same thread
        held[key] += 1
        try:
            yield
        finally:
            held[key] -= 1
        return
    with _guard:
        tl = _tlocks.setdefault(key, threading.Lock())
    if not tl.acquire(timeout=max(timeout, 0.001)):
        raise LockBusy(f"{name} is busy in this process")
    t0 = time.time()
    try:
        while True:
            try:
                fd = os.open(f, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()} {time.time()}".encode())
                os.close(fd)
                break
            except FileExistsError:
                try:
                    if time.time() - f.stat().st_mtime > stale:
                        f.unlink()                              # abandoned by a crashed process
                        continue
                except FileNotFoundError:
                    continue
                except PermissionError:
                    pass
                if time.time() - t0 >= timeout:
                    raise LockBusy(f"{name} is held by another process")
                time.sleep(0.03)
        held[key] = 1
        try:
            yield
        finally:
            held.pop(key, None)
            for _ in range(50):
                try:
                    f.unlink()
                    break
                except FileNotFoundError:
                    break
                except PermissionError:
                    time.sleep(0.02)
    finally:
        tl.release()
