#!/usr/bin/env python3

"""Calculate a conservative HFS+ image capacity for a staged macOS app."""

from __future__ import annotations

import argparse
import ctypes
from functools import lru_cache
import os
from pathlib import Path
import sys


ALLOCATION_BLOCK_BYTES = 4 * 1024
CATALOG_RESERVE_BYTES_PER_ENTRY = 2 * ALLOCATION_BLOCK_BYTES
FILESYSTEM_RESERVE_BYTES = 256 * 1024 * 1024
IMAGE_SIZE_QUANTUM_BYTES = 64 * 1024 * 1024
MEBIBYTE_BYTES = 1024 * 1024
XATTR_NOFOLLOW = 0x0001


def _round_up(value: int, quantum: int) -> int:
    return ((value + quantum - 1) // quantum) * quantum


def _walk_without_following_symlinks(root: Path):
    pending = [root]
    while pending:
        path = pending.pop()
        yield path
        if path.is_symlink() or not path.is_dir():
            continue
        with os.scandir(path) as entries:
            pending.extend(Path(entry.path) for entry in entries)


def _raise_native_error(operation: str, path: Path) -> None:
    error_number = ctypes.get_errno()
    raise OSError(
        error_number,
        f"{operation} failed: {os.strerror(error_number)}",
        path,
    )


@lru_cache(maxsize=1)
def _darwin_xattr_api():
    libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    list_xattrs = libc.listxattr
    list_xattrs.argtypes = [
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_int,
    ]
    list_xattrs.restype = ctypes.c_ssize_t
    get_xattr = libc.getxattr
    get_xattr.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_uint32,
        ctypes.c_int,
    ]
    get_xattr.restype = ctypes.c_ssize_t
    return list_xattrs, get_xattr


def _darwin_extended_attributes(path: Path) -> list[tuple[bytes, int]]:
    list_xattrs, get_xattr = _darwin_xattr_api()

    encoded_path = os.fsencode(path)
    names_size = list_xattrs(encoded_path, None, 0, XATTR_NOFOLLOW)
    if names_size < 0:
        _raise_native_error("listxattr", path)
    if names_size == 0:
        return []

    names_buffer = ctypes.create_string_buffer(names_size)
    returned_size = list_xattrs(
        encoded_path,
        ctypes.cast(names_buffer, ctypes.c_void_p),
        names_size,
        XATTR_NOFOLLOW,
    )
    if returned_size < 0:
        _raise_native_error("listxattr", path)
    attribute_names = names_buffer.raw[:returned_size].rstrip(b"\0").split(b"\0")

    attributes = []
    for attribute_name in attribute_names:
        value_size = get_xattr(
            encoded_path,
            attribute_name,
            None,
            0,
            0,
            XATTR_NOFOLLOW,
        )
        if value_size < 0:
            _raise_native_error(
                f"getxattr({os.fsdecode(attribute_name)})", path
            )
        attributes.append((attribute_name, value_size))
    return attributes


def _extended_attributes(path: Path) -> list[tuple[bytes, int]]:
    if sys.platform == "darwin":
        return _darwin_extended_attributes(path)
    if not hasattr(os, "listxattr") or not hasattr(os, "getxattr"):
        raise RuntimeError(
            f"extended-attribute inspection is unavailable on {sys.platform}"
        )
    return [
        (
            os.fsencode(attribute_name),
            len(os.getxattr(path, attribute_name, follow_symlinks=False)),
        )
        for attribute_name in os.listxattr(path, follow_symlinks=False)
    ]


def calculate_image_size(root: Path) -> dict[str, int]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"macOS bundle path is not a directory: {root}")

    entry_count = 0
    data_bytes = 0
    extended_attribute_bytes = 0
    for path in _walk_without_following_symlinks(root):
        entry_count += 1
        stat_result = path.lstat()
        data_bytes += _round_up(stat_result.st_size, ALLOCATION_BLOCK_BYTES)
        for attribute_name, attribute_value_size in _extended_attributes(path):
            attribute_record_bytes = (
                len(attribute_name) + attribute_value_size + 64
            )
            extended_attribute_bytes += _round_up(
                attribute_record_bytes, ALLOCATION_BLOCK_BYTES
            )

    catalog_reserve_bytes = entry_count * CATALOG_RESERVE_BYTES_PER_ENTRY
    required_bytes = (
        data_bytes
        + extended_attribute_bytes
        + catalog_reserve_bytes
        + FILESYSTEM_RESERVE_BYTES
    )
    image_bytes = _round_up(required_bytes, IMAGE_SIZE_QUANTUM_BYTES)
    return {
        "entries": entry_count,
        "data_bytes": data_bytes,
        "extended_attribute_bytes": extended_attribute_bytes,
        "catalog_reserve_bytes": catalog_reserve_bytes,
        "filesystem_reserve_bytes": FILESYSTEM_RESERVE_BYTES,
        "image_bytes": image_bytes,
    }


def format_hdiutil_size(image_bytes: int) -> str:
    """Return an exact hdiutil size without the ambiguous sector suffix."""
    if image_bytes <= 0 or image_bytes % MEBIBYTE_BYTES:
        raise ValueError("image capacity must be a positive whole MiB value")
    return f"{image_bytes // MEBIBYTE_BYTES}m"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("app_bundle", type=Path)
    args = parser.parse_args()

    estimate = calculate_image_size(args.app_bundle)
    print(
        "macOS DMG capacity audit: "
        + " ".join(f"{key}={value}" for key, value in estimate.items()),
        file=sys.stderr,
    )
    print(format_hdiutil_size(estimate["image_bytes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
