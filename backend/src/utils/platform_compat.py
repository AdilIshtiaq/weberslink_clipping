"""Small helpers so the backend also runs on Windows.

``fcntl`` only exists on Unix. Everything here is a no-op or the real module on Linux and macOS,
so behaviour there is unchanged.
"""

from __future__ import annotations

import errno
import os
import threading
import time
import types
import weakref

LOCK_SH = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8


def _make_windows_flock(msvcrt):
    """Build an ``fcntl.flock`` stand-in on top of ``msvcrt.locking``.

    Windows has no shared locks, so a shared request takes the exclusive lock (stricter, never
    unsafe). ``flock`` lets one handle re-lock or upgrade a lock it already holds; Windows would
    refuse that, so a lock the handle already holds counts as acquired.
    """
    held_objects: "weakref.WeakSet" = weakref.WeakSet()
    held_fds: set[int] = set()
    guard = threading.Lock()

    def key_state(handle):
        if isinstance(handle, int):
            return handle, handle in held_fds
        return handle, handle in held_objects

    def mark(handle, locked: bool) -> None:
        with guard:
            if isinstance(handle, int):
                (held_fds.add if locked else held_fds.discard)(handle)
            else:
                try:
                    (held_objects.add if locked else held_objects.discard)(handle)
                except TypeError:  # not weak-referenceable: fall back to the descriptor number
                    (held_fds.add if locked else held_fds.discard)(handle.fileno())

    def flock(handle, operation: int) -> None:
        fd = handle if isinstance(handle, int) else handle.fileno()
        _, already = key_state(handle)
        position = os.lseek(fd, 0, os.SEEK_CUR)
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            if operation & LOCK_UN:
                try:
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass  # nothing was locked
                mark(handle, False)
                return
            if already:
                return
            nonblocking = bool(operation & LOCK_NB)
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    mark(handle, True)
                    return
                except OSError as exc:
                    if nonblocking:
                        raise BlockingIOError(errno.EWOULDBLOCK, "Resource temporarily unavailable") from exc
                    time.sleep(0.05)
        finally:
            os.lseek(fd, position, os.SEEK_SET)

    return flock


if os.name == "nt":  # pragma: no cover - exercised on Windows only
    import msvcrt

    fcntl = types.SimpleNamespace(
        flock=_make_windows_flock(msvcrt),
        LOCK_SH=LOCK_SH,
        LOCK_EX=LOCK_EX,
        LOCK_NB=LOCK_NB,
        LOCK_UN=LOCK_UN,
    )
else:
    import fcntl  # noqa: F401


def fsync_directory(path) -> None:
    """Flush a directory entry to disk. Windows cannot open directories this way and does not need it."""
    if os.name == "nt":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
