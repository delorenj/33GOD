#!/usr/bin/env python3
"""Shared fail-closed runtime primitives for root acceptance validators."""

from __future__ import annotations

import errno
import os
import selectors
import signal
import stat
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable, Iterator, Mapping, Sequence


PROCESS_CLEANUP_SECONDS = 2.0
FULL_OBJECT_ID_LENGTH = 40
VALID_OBJECT_TYPES = {b"blob", b"commit", b"tag", b"tree"}

GitExecutor = Callable[
    [Sequence[str], bytes | None, int, frozenset[int]],
    subprocess.CompletedProcess[bytes],
]


class BoundedProcessError(RuntimeError):
    """A child crossed a resource boundary without retaining its payload."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class ValidationBudget:
    """Invocation-wide limits shared by Git, traversal, and retained inputs."""

    wall_seconds: float = 120.0
    max_git_calls: int = 16_384
    max_entries: int = 100_000
    max_files: int = 25_000
    max_matches: int = 100_000
    max_findings: int = 10_000
    max_retained_bytes: int = 64_000_000
    started: float = field(default_factory=time.monotonic)
    git_calls: int = 0
    entries: int = 0
    files: int = 0
    matches: int = 0
    findings: int = 0
    retained_bytes: int = 0

    def check_time(self) -> None:
        if time.monotonic() - self.started > self.wall_seconds:
            raise ValueError("validation exceeded its invocation-wide time bound")

    def remaining_seconds(self, per_operation_limit: float) -> float:
        """Return a positive timeout that cannot exceed the invocation deadline."""

        remaining = self.wall_seconds - (time.monotonic() - self.started)
        if remaining <= 0:
            raise ValueError("validation exceeded its invocation-wide time bound")
        return min(per_operation_limit, remaining)

    def consume(self, resource: str, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("validation resource consumption must be non-negative")
        self.check_time()
        attribute = {
            "git_calls": "git_calls",
            "entries": "entries",
            "files": "files",
            "matches": "matches",
            "findings": "findings",
            "retained_bytes": "retained_bytes",
        }.get(resource)
        limit_attribute = {
            "git_calls": "max_git_calls",
            "entries": "max_entries",
            "files": "max_files",
            "matches": "max_matches",
            "findings": "max_findings",
            "retained_bytes": "max_retained_bytes",
        }.get(resource)
        if attribute is None or limit_attribute is None:
            raise ValueError(f"unknown validation resource: {resource}")
        value = int(getattr(self, attribute)) + amount
        if value > int(getattr(self, limit_attribute)):
            label = resource.replace("_", " ")
            raise ValueError(f"validation exceeded its invocation-wide {label} bound")
        setattr(self, attribute, value)


def sanitized_git_environment(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Remove every ambient Git control and add only explicit safe controls."""

    inherited = os.environ if source is None else source
    environment = {
        key: value
        for key, value in inherited.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def sanitized_command_environment(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return a small non-secret environment for committed candidate programs."""

    inherited = os.environ if source is None else source
    allowed = {
        "DOCKER_CONTEXT",
        "DOCKER_HOST",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "PATH",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "WINDIR",
        "XDG_RUNTIME_DIR",
    }
    environment = {key: value for key, value in inherited.items() if key in allowed}
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def terminate_process_group(
    process: subprocess.Popen[bytes],
    *,
    cleanup_seconds: float = PROCESS_CLEANUP_SECONDS,
) -> bool:
    """Kill the whole isolated group and reap the leader within one deadline."""

    deadline = time.monotonic() + max(0.0, cleanup_seconds)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        if process.poll() is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass

    remaining = deadline - time.monotonic()
    if remaining > 0:
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            remaining = deadline - time.monotonic()
            if remaining > 0:
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    return False
            else:
                return False
    elif process.poll() is None:
        return False

    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        time.sleep(0.01)
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def run_bounded_process(
    command: Sequence[str],
    *,
    input_bytes: bytes | None = None,
    stdout_limit: int,
    stderr_limit: int,
    timeout: float,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    pass_fds: Sequence[int] = (),
) -> subprocess.CompletedProcess[bytes]:
    """Stream a child through byte/time caps and clean its complete process group."""

    if not command or stdout_limit < 0 or stderr_limit < 0 or timeout <= 0:
        raise ValueError("invalid bounded subprocess configuration")
    process = subprocess.Popen(
        list(command),
        stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        env=None if env is None else dict(env),
        cwd=None if cwd is None else os.fspath(cwd),
        close_fds=True,
        pass_fds=tuple(pass_fds),
    )
    if process.stdout is None or process.stderr is None:
        terminate_process_group(process)
        raise BoundedProcessError("pipe")

    selector = selectors.DefaultSelector()
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": stdout_limit, "stderr": stderr_limit}
    input_view = memoryview(input_bytes or b"")
    input_offset = 0
    deadline = time.monotonic() + timeout
    try:
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        if process.stdin is not None:
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")

        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BoundedProcessError("timeout")
            events = selector.select(remaining)
            if not events:
                raise BoundedProcessError("timeout")
            for key, _mask in events:
                stream = key.fileobj
                name = str(key.data)
                if name == "stdin":
                    if input_offset >= len(input_view):
                        selector.unregister(stream)
                        stream.close()
                        continue
                    try:
                        written = os.write(
                            stream.fileno(), input_view[input_offset : input_offset + 65536]
                        )
                    except BrokenPipeError:
                        selector.unregister(stream)
                        stream.close()
                    else:
                        input_offset += written
                    continue

                capacity = limits[name] - len(streams[name])
                try:
                    chunk = os.read(stream.fileno(), min(65536, capacity + 1))
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                    continue
                streams[name].extend(chunk)
                if len(streams[name]) > limits[name]:
                    streams[name].clear()
                    raise BoundedProcessError("output")

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BoundedProcessError("timeout")
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise BoundedProcessError("timeout") from exc
    except BaseException as exc:
        for payload in streams.values():
            payload.clear()
        if not terminate_process_group(process):
            raise BoundedProcessError("cleanup") from exc
        raise
    finally:
        selector.close()
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        for stream in (process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()

    return subprocess.CompletedProcess(
        list(command),
        returncode,
        bytes(streams["stdout"]),
        bytes(streams["stderr"]),
    )


def verify_local_git_object_closure(
    repo: Path,
    revision: str,
    execute: GitExecutor,
    *,
    max_objects: int = 100_000,
    max_output_bytes: int = 16_000_000,
) -> None:
    """Verify a complete, non-promisor, locally readable exact commit closure."""

    def run(
        *args: str,
        input_bytes: bytes | None = None,
        allowed: frozenset[int] = frozenset({0}),
    ) -> subprocess.CompletedProcess[bytes]:
        return execute(args, input_bytes, max_output_bytes, allowed)

    def one_line(*args: str) -> bytes:
        lines = run(*args).stdout.splitlines()
        if len(lines) != 1 or not lines[0]:
            raise ValueError("Git returned malformed local object metadata")
        return lines[0]

    if (
        len(revision) != FULL_OBJECT_ID_LENGTH
        or any(character not in "0123456789abcdef" for character in revision)
    ):
        raise ValueError("invalid exact Git commit revision")
    if one_line("cat-file", "-t", revision) != b"commit":
        raise ValueError("exact Git revision is missing or is not a commit")

    shallow = one_line("rev-parse", "--is-shallow-repository")
    if shallow not in {b"true", b"false"}:
        raise ValueError("Git returned malformed shallow-repository metadata")
    if shallow == b"true":
        raise ValueError("shallow repositories are not valid provenance sources")

    partial = run(
        "config",
        "--local",
        "--get-regexp",
        r"^(extensions\.partialClone|remote\..*\.(promisor|partialclonefilter))$",
        allowed=frozenset({0, 1}),
    )
    if partial.returncode == 0 or partial.stdout:
        raise ValueError("partial or promisor repositories are not valid provenance sources")

    object_path = Path(
        one_line("rev-parse", "--path-format=absolute", "--git-path", "objects")
        .decode("utf-8", errors="strict")
    )
    shallow_path = Path(
        one_line("rev-parse", "--path-format=absolute", "--git-path", "shallow")
        .decode("utf-8", errors="strict")
    )
    alternates = object_path / "info/alternates"
    if alternates.exists() or alternates.is_symlink():
        raise ValueError("alternate object directories are not valid provenance sources")
    try:
        promisor_packs = tuple((object_path / "pack").glob("*.promisor"))
    except OSError as exc:
        raise ValueError("Git object storage cannot be inspected safely") from exc
    if promisor_packs:
        raise ValueError("promisor packs are not valid provenance sources")
    if shallow_path.exists() or shallow_path.is_symlink():
        raise ValueError("shallow metadata is not valid for provenance validation")

    raw_objects = run(
        "rev-list",
        "--objects",
        "--no-object-names",
        "--missing=print",
        revision,
    ).stdout
    object_ids: list[bytes] = []
    seen: set[bytes] = set()
    for line in raw_objects.splitlines():
        if line.startswith(b"?"):
            raise ValueError("exact Git closure contains a promised or missing object")
        if (
            len(line) != FULL_OBJECT_ID_LENGTH
            or any(character not in b"0123456789abcdef" for character in line)
        ):
            raise ValueError("Git returned malformed exact object closure data")
        if line not in seen:
            seen.add(line)
            object_ids.append(line)
            if len(object_ids) > max_objects:
                raise ValueError("exact Git closure exceeds its finite object bound")
    if revision.encode("ascii") not in seen:
        raise ValueError("exact Git closure omitted its requested commit")

    payload = b"\n".join(object_ids) + b"\n"
    checked = run(
        "cat-file",
        "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        input_bytes=payload,
    ).stdout.splitlines()
    if len(checked) != len(object_ids):
        raise ValueError("Git object verification returned malformed data")
    for expected, line in zip(object_ids, checked, strict=True):
        fields = line.split(b" ")
        if (
            len(fields) != 3
            or fields[0] != expected
            or fields[1] not in VALID_OBJECT_TYPES
            or not fields[2].isdigit()
        ):
            raise ValueError("exact Git closure contains a missing or invalid object")

    # Unlike --connectivity-only, full fsck reads and hashes object contents,
    # including packed blobs. Lazy fetch and replacement refs are disabled by
    # the caller's sanitized environment.
    run(
        "-c",
        "fsck.gitmodulesSymlink=ignore",
        "fsck",
        "--full",
        "--no-dangling",
        "--no-reflogs",
        revision,
    )


@dataclass
class BoundDirectory:
    """A directory inode held open across all identity checks."""

    root: Path
    relative: PurePosixPath
    fd: int
    device: int
    inode: int

    @property
    def process_path(self) -> Path:
        proc_path = Path(f"/proc/self/fd/{self.fd}")
        if not proc_path.exists():
            raise OSError("descriptor-relative process path is unavailable")
        return proc_path

    def canonical_path_matches(self) -> bool:
        try:
            with open_bound_directory(self.root, self.relative) as current:
                return (current.device, current.inode) == (self.device, self.inode)
        except OSError:
            return False

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


@contextmanager
def open_bound_directory(
    root: Path,
    relative: str | PurePosixPath,
) -> Iterator[BoundDirectory]:
    """Open every directory component with no-follow semantics."""

    relative_path = PurePosixPath(str(relative))
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or any(part in {"", ".", ".."} for part in relative_path.parts)
    ):
        raise OSError(errno.EINVAL, "invalid descriptor-relative directory path")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    root_fd = os.open(root, flags)
    current_fd = root_fd
    try:
        for part in relative_path.parts:
            next_fd = os.open(part, flags, dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        metadata = os.fstat(current_fd)
        if not stat.S_ISDIR(metadata.st_mode):
            raise OSError(errno.ENOTDIR, "bound checkout is not a directory")
        if current_fd == root_fd:
            raise OSError(errno.EINVAL, "bound checkout cannot equal its root")
        bound = BoundDirectory(
            Path(root),
            relative_path,
            current_fd,
            metadata.st_dev,
            metadata.st_ino,
        )
        current_fd = -1
        yield bound
    finally:
        if current_fd >= 0:
            os.close(current_fd)
        os.close(root_fd)
        if "bound" in locals():
            bound.close()
