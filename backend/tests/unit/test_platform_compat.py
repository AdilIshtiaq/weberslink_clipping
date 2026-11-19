"""Windows file locking, tested against a fake ``msvcrt`` so it runs on any platform."""

import os
import threading
import time
from types import SimpleNamespace

import pytest

from src.utils import platform_compat as pc


class FakeMsvcrt:
    """Mimics Windows byte-range locks: one owner per file, and no re-locking even by the same handle."""

    LK_NBLCK = 2
    LK_UNLCK = 0

    def __init__(self):
        self.owners = {}
        self.mutex = threading.Lock()

    def locking(self, fd, mode, nbytes):
        stat = os.fstat(fd)
        key = (stat.st_dev, stat.st_ino)
        with self.mutex:
            if mode == self.LK_UNLCK:
                if self.owners.get(key) != fd:
                    raise OSError("not locked")
                del self.owners[key]
                return
            if key in self.owners:
                raise OSError("locked")
            self.owners[key] = fd


@pytest.fixture
def flock():
    return pc._make_windows_flock(FakeMsvcrt())


def test_nonblocking_conflict_raises_blocking_io_error(tmp_path, flock):
    target = tmp_path / "lock"
    target.write_text("x")
    with target.open("rb") as first, target.open("rb") as second:
        flock(first, pc.LOCK_EX | pc.LOCK_NB)
        with pytest.raises(BlockingIOError):
            flock(second, pc.LOCK_EX | pc.LOCK_NB)
        flock(first, pc.LOCK_UN)
        flock(second, pc.LOCK_EX | pc.LOCK_NB)  # free again


def test_blocking_lock_waits_for_release(tmp_path, flock):
    target = tmp_path / "lock"
    target.write_text("x")
    first = target.open("rb")
    second = target.open("rb")
    flock(first, pc.LOCK_EX)
    acquired = []

    def other():
        flock(second, pc.LOCK_EX)
        acquired.append(time.monotonic())

    worker = threading.Thread(target=other)
    worker.start()
    time.sleep(0.2)
    assert not acquired
    flock(first, pc.LOCK_UN)
    worker.join(timeout=5)
    assert acquired
    first.close()
    second.close()


def test_relocking_or_upgrading_a_held_lock_succeeds(tmp_path, flock):
    target = tmp_path / "lock"
    target.write_text("x")
    with target.open("rb") as handle:
        flock(handle, pc.LOCK_SH)
        flock(handle, pc.LOCK_EX)  # shared -> exclusive on the same handle
        flock(handle, pc.LOCK_UN)


def test_file_position_is_restored(tmp_path, flock):
    target = tmp_path / "lock"
    target.write_bytes(b"0123456789")
    with target.open("rb") as handle:
        handle.seek(4)
        flock(handle, pc.LOCK_EX)
        assert handle.tell() == 4
        assert handle.read(2) == b"45"
        flock(handle, pc.LOCK_UN)


def test_integer_descriptors_work(tmp_path, flock):
    target = tmp_path / "lock"
    target.write_text("x")
    fd = os.open(target, os.O_RDWR)
    try:
        flock(fd, pc.LOCK_EX | pc.LOCK_NB)
        flock(fd, pc.LOCK_UN)
    finally:
        os.close(fd)


def test_exports_match_the_fcntl_api():
    assert callable(pc.fcntl.flock)
    for name in ("LOCK_SH", "LOCK_EX", "LOCK_NB", "LOCK_UN"):
        assert isinstance(getattr(pc.fcntl, name), int)


def test_fsync_directory_runs(tmp_path):
    pc.fsync_directory(tmp_path)
