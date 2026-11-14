#!/usr/bin/env python3
"""Byte-reproducibility helpers for ``make release``.

setuptools does not apply ``SOURCE_DATE_EPOCH`` to sdist tar members: two
``uv build`` runs of the same commit give an identical wheel but an sdist that
differs only in member mtimes and the gzip header mtime. This module normalises
ONLY that archive envelope:

* members sorted by name;
* every member mtime = ``SOURCE_DATE_EPOCH``;
* uid/gid 0, uname/gname empty;
* gzip header mtime 0 and no embedded file name.

File contents, member names, types, modes and link targets are carried over
unchanged, and :func:`normalise_sdist` proves it: the per-member content digest
of the archive before and after must be identical, or it raises.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import tarfile
from collections.abc import Iterable
from pathlib import Path

CHUNK = 1 << 20


class ReproducibilityError(Exception):
    """An archive could not be normalised without touching its contents."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def member_digests(archive: Path) -> dict[str, str]:
    """Map each member name to a digest of what it carries (not its envelope).

    Regular files: sha256 of the bytes. Directories: ``dir``. Links: the target.
    Mode is included, so a normalisation that changed permissions would be caught.
    """
    digests: dict[str, str] = {}
    with tarfile.open(archive, mode="r:*") as tar:
        for member in tar.getmembers():
            if member.name in digests:
                raise ReproducibilityError(f"{archive.name}: duplicate member {member.name}")
            mode = f"{member.mode:o}"
            if member.isfile():
                extracted = tar.extractfile(member)
                if extracted is None:
                    raise ReproducibilityError(f"{archive.name}: unreadable member {member.name}")
                digest = hashlib.sha256(extracted.read()).hexdigest()
                digests[member.name] = f"file:{mode}:{digest}"
            elif member.isdir():
                digests[member.name] = f"dir:{mode}"
            elif member.issym() or member.islnk():
                kind = "sym" if member.issym() else "hard"
                digests[member.name] = f"{kind}:{mode}:{member.linkname}"
            else:
                raise ReproducibilityError(
                    f"{archive.name}: unsupported member type for {member.name}"
                )
    return digests


def _normalised_members(
    tar: tarfile.TarFile, epoch: int
) -> Iterable[tuple[tarfile.TarInfo, bytes | None]]:
    for member in sorted(tar.getmembers(), key=lambda item: item.name):
        info = tarfile.TarInfo(member.name)
        info.type = member.type
        info.mode = member.mode
        info.linkname = member.linkname
        info.size = member.size if member.isfile() else 0
        info.mtime = epoch
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        data: bytes | None = None
        if member.isfile():
            extracted = tar.extractfile(member)
            if extracted is None:
                raise ReproducibilityError(f"unreadable member {member.name}")
            data = extracted.read()
        yield info, data


def normalise_sdist(archive: Path, epoch: int) -> dict[str, str]:
    """Rewrite a ``.tar.gz`` sdist's envelope in place; return its member digests.

    Raises ReproducibilityError if the member set or any member's content
    digest differs before vs after.
    """
    if not archive.name.endswith(".tar.gz"):
        raise ReproducibilityError(f"{archive.name}: not a .tar.gz sdist")
    before = member_digests(archive)
    tar_bytes = io.BytesIO()
    with tarfile.open(archive, mode="r:gz") as source:
        with tarfile.open(fileobj=tar_bytes, mode="w", format=tarfile.PAX_FORMAT) as target:
            for info, data in _normalised_members(source, epoch):
                target.addfile(info, io.BytesIO(data) if data is not None else None)
    raw = io.BytesIO()
    # filename="" keeps the name out of the header; mtime=0 fixes the header time.
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz:
        gz.write(tar_bytes.getvalue())
    archive.write_bytes(raw.getvalue())
    after = member_digests(archive)
    if before != after:
        changed = sorted(set(before.items()) ^ set(after.items()))
        raise ReproducibilityError(
            f"{archive.name}: normalisation changed member contents: {changed[:5]}"
        )
    return after


def write_sha256sums(directory: Path, names: Iterable[str]) -> Path:
    """Write ``SHA256SUMS`` in ``sha256sum -c`` format, sorted by name."""
    lines = [f"{sha256_file(directory / name)}  {name}\n" for name in sorted(names)]
    target = directory / "SHA256SUMS"
    target.write_text("".join(lines), encoding="utf-8")
    return target
