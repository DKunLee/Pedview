from __future__ import annotations

import re
from collections.abc import Mapping

AFFECTED_METADATA_KEYS = ("affected", "affection", "phenotype")


def normalize_metadata_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")


def normalize_affected_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized in {
        "2",
        "affected",
        "case",
        "yes",
        "y",
        "true",
        "t",
        "positive",
        "present",
    }:
        return "affected"
    if normalized in {
        "1",
        "unaffected",
        "control",
        "no",
        "n",
        "false",
        "f",
        "negative",
        "absent",
    }:
        return "unaffected"
    if normalized in {
        "0",
        "-9",
        ".",
        "na",
        "n/a",
        "none",
        "null",
        "unknown",
        "u",
        "missing",
    }:
        return "unknown"
    return None


def affected_metadata_key(metadata: Mapping[str, str] | None) -> str | None:
    if not metadata:
        return None
    for alias in AFFECTED_METADATA_KEYS:
        for key in metadata.keys():
            if normalize_metadata_key(key) == alias:
                return key
    return None


def affected_status_from_metadata(metadata: Mapping[str, str] | None) -> str | None:
    if not metadata:
        return None
    key = affected_metadata_key(metadata)
    if key is None:
        return None
    return normalize_affected_status(metadata.get(key))


def metadata_without_affected_status(
    metadata: Mapping[str, str] | None,
) -> dict[str, str]:
    if not metadata:
        return {}
    key = affected_metadata_key(metadata)
    status = affected_status_from_metadata(metadata)
    if key is None or status is None:
        return dict(metadata)
    return {
        entry_key: value for entry_key, value in metadata.items() if entry_key != key
    }
