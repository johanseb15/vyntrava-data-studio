"""Resolve paths inside one client's job without creating or opening files."""

import os
from pathlib import Path
import re
import stat
import unicodedata


_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_OUTPUT_KINDS = frozenset({"trabajo", "salidas", "evidencia"})
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class WorkspaceError(ValueError):
    """A path was rejected; code is stable and the message contains no path."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise WorkspaceError("invalid_identifier")
    return value


def _basename(value: str) -> str:
    if (not isinstance(value, str) or not value or value in {".", ".."}
            or any(character in value for character in "/\\:")
            or any(unicodedata.category(character) == "Cc" for character in value)):
        raise WorkspaceError("invalid_basename")
    return value


def _status(path: Path) -> os.stat_result | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise WorkspaceError("inaccessible_path") from exc
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE_POINT:
        raise WorkspaceError("redirected_path")
    return info


def _directory(path: Path) -> None:
    info = _status(path)
    if info is None:
        raise WorkspaceError("missing_workspace")
    if not stat.S_ISDIR(info.st_mode):
        raise WorkspaceError("not_directory")


def _workspace(root: Path, client: str, job: str, folder: str) -> Path:
    _identifier(client)
    _identifier(job)
    try:
        root = Path(root).absolute()
    except (TypeError, ValueError) as exc:
        raise WorkspaceError("invalid_root") from exc
    for component in (*reversed(root.parents), root):
        _directory(component)
    client_path = root / client
    _directory(client_path)
    job_path = client_path / job
    _directory(job_path)
    folder_path = job_path / folder
    _directory(folder_path)
    canonical_job = job_path.resolve(strict=True)
    canonical_folder = folder_path.resolve(strict=True)
    if canonical_folder.parent != canonical_job:
        raise WorkspaceError("outside_workspace")
    return canonical_folder


def resolve_input(root: Path, client: str, job: str, basename: str) -> Path:
    """Return an existing regular file in originales after checking its route."""
    name = _basename(basename)
    folder = _workspace(root, client, job, "originales")
    target = folder / name
    info = _status(target)
    if info is None:
        raise WorkspaceError("missing_input")
    if not stat.S_ISREG(info.st_mode):
        raise WorkspaceError("not_regular_file")
    canonical_target = target.resolve(strict=True)
    if canonical_target.parent != folder:
        raise WorkspaceError("outside_workspace")
    return canonical_target


def resolve_output(root: Path, client: str, job: str, basename: str,
                   kind: str) -> Path:
    """Return a free path in trabajo, salidas or evidencia, without writing."""
    name = _basename(basename)
    if not isinstance(kind, str) or kind not in _OUTPUT_KINDS:
        raise WorkspaceError("invalid_output_kind")
    folder = _workspace(root, client, job, kind)
    target = folder / name
    if _status(target) is not None:
        raise WorkspaceError("output_exists")
    if target.resolve(strict=False).parent != folder:
        raise WorkspaceError("outside_workspace")
    return target
