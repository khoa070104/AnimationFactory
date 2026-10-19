"""Machine-wide limit on concurrent agy runs (image jobs and LLM calls), shared by every process (UI server, MCP server, CLI).
A slot is a lock file created exclusively in phase2/.locks/; it records its owner (pid + process start stamp). A slot whose owner is gone
is taken over, so a crashed process never blocks the others. The number of slots comes from config.json {"ai": {"agy_concurrency": N}} (default 1)."""
import ctypes
import json
import os
import time
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
LOCKS = Path(os.environ.get("AF_LOCKS") or (P2 / ".locks"))


def proc_stamp(pid):
    """A value that identifies one incarnation of a process (its creation time), or None if the process does not exist (any more)."""
    if os.name == "nt":
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        k.OpenProcess.restype = wintypes.HANDLE
        h = k.OpenProcess(0x1000, False, int(pid))                          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return None
        try:
            code = wintypes.DWORD()
            if not k.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:   # 259 = STILL_ACTIVE
                return None
            c, e, kt, ut = (wintypes.FILETIME() for _ in range(4))
            if not k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut)):
                return None
            return f"{c.dwHighDateTime}:{c.dwLowDateTime}"
        finally:
            k.CloseHandle(h)
    try:
        return open(f"/proc/{int(pid)}/stat", encoding="utf-8").read().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        try:
            os.kill(int(pid), 0)
            return "alive"
        except OSError:
            return None


def limit():
    n = os.environ.get("AF_AGY_CONCURRENCY")
    if not n:
        cfg = P2 / "config.json"
        if cfg.exists():
            n = (json.loads(cfg.read_text(encoding="utf-8")).get("ai") or {}).get("agy_concurrency")
    return max(1, int(n or 1))


class SlotTimeout(RuntimeError):
    pass


class AgySlot:
    """with AgySlot("image coin"):  ... run agy ...   -> blocks until one of the machine-wide slots is free."""

    def __init__(self, label="", timeout=1800, slots=None):
        self.label, self.timeout, self.slots = label, timeout, slots or limit()
        self.path = None

    def _owner_alive(self, f):
        try:
            o = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            try:
                return time.time() - f.stat().st_mtime < 5                  # created a moment ago, owner not written yet
            except OSError:
                return False
        return bool(o.get("pid")) and proc_stamp(o["pid"]) == o.get("stamp")

    def __enter__(self):
        LOCKS.mkdir(parents=True, exist_ok=True)
        end = time.time() + self.timeout
        me = json.dumps({"pid": os.getpid(), "stamp": proc_stamp(os.getpid()), "label": self.label, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        while True:
            for i in range(self.slots):
                f = LOCKS / f"agy_slot_{i}.lock"
                try:
                    fd = os.open(f, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                except FileExistsError:
                    if not self._owner_alive(f):
                        try:
                            f.unlink()                                       # owner died: take the slot over on the next pass
                        except OSError:
                            pass
                    continue
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(me)
                self.path = f
                return self
            if time.time() > end:
                raise SlotTimeout(f"all {self.slots} agy slot(s) stayed busy for {self.timeout}s")
            time.sleep(0.25)

    def __exit__(self, *a):
        if self.path:
            try:
                self.path.unlink()
            except OSError:
                pass


def status():
    """-> [{slot, busy, owner...}] for the UI / evidence."""
    out = []
    for i in range(limit()):
        f = LOCKS / f"agy_slot_{i}.lock"
        row = {"slot": i, "busy": False}
        if f.exists():
            try:
                o = json.loads(f.read_text(encoding="utf-8"))
                row.update(o, busy=bool(o.get("pid")) and proc_stamp(o["pid"]) == o.get("stamp"))
            except (OSError, ValueError):
                row["busy"] = True
        out.append(row)
    return out
