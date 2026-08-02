"""Idempotent planning helpers for importing Google Drive tender folders.

The runtime importer consumes a non-secret manifest of Drive folder/file metadata.
It never stores Drive credentials and never mutates source files.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping


@dataclass(frozen=True)
class TenderFolder:
    drive_folder_id: str
    name: str
    url: str
    files: tuple[Mapping[str, str], ...] = ()


@dataclass(frozen=True)
class ImportDecision:
    action: str
    canonical_name: str
    source_folder_ids: tuple[str, ...]
    reason: str


def normalize_tender_name(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    replacements = {
        "sani": "sanitary",
        "voc": "village of cumberland",
        "itt": "",
    }
    tokens = [replacements.get(token, token) for token in value.split()]
    return " ".join(token for token in tokens if token)


def extract_reference(value: str) -> str | None:
    patterns = (
        r"\bITT[- ]?\d{3,}\b",
        r"\bQ\d{2}[- ]?\d{3}\b",
        r"\b\d{4}-\d{4,}-\d{2}\b",
        r"\b\d{4}-\d{2}-[A-Z0-9-]+\b",
    )
    upper = value.upper()
    for pattern in patterns:
        match = re.search(pattern, upper)
        if match:
            return re.sub(r"\s+", "-", match.group(0))
    return None


def plan_import(folders: Iterable[TenderFolder]) -> list[ImportDecision]:
    """Return deterministic create/consolidate decisions for a dry run.

    Folder IDs are stable external identifiers. Matching prioritizes tender/reference
    numbers and then uses normalized project names plus contained filenames.
    """
    groups: list[list[TenderFolder]] = []
    for folder in sorted(folders, key=lambda item: item.drive_folder_id):
        reference = extract_reference(folder.name)
        normalized = normalize_tender_name(folder.name)
        matched: list[TenderFolder] | None = None
        for group in groups:
            group_references = {extract_reference(item.name) for item in group}
            group_names = {normalize_tender_name(item.name) for item in group}
            if reference and reference in group_references:
                matched = group
                break
            if any(_names_overlap(normalized, candidate) for candidate in group_names):
                matched = group
                break
        if matched is None:
            groups.append([folder])
        else:
            matched.append(folder)

    decisions: list[ImportDecision] = []
    for group in groups:
        canonical = max(group, key=lambda item: (len(item.name), item.name)).name.strip()
        action = "consolidate" if len(group) > 1 else "create_or_update"
        reason = (
            "matching tender/reference number or normalized project identity"
            if len(group) > 1
            else "distinct Drive tender folder"
        )
        decisions.append(
            ImportDecision(
                action=action,
                canonical_name=canonical,
                source_folder_ids=tuple(sorted(item.drive_folder_id for item in group)),
                reason=reason,
            )
        )
    return sorted(decisions, key=lambda item: item.canonical_name.casefold())


def _names_overlap(left: str, right: str) -> bool:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    significant = {"sewer", "sanitary", "manhole", "fernie", "cumberland", "firehall", "storm"}
    common = left_tokens & right_tokens
    return len(common) >= 3 or len(common & significant) >= 2
