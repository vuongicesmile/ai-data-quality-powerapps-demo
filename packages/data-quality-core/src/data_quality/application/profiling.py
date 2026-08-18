"""Deterministic schema discovery and bounded column profiling."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from data_quality.domain.models import ColumnProfile

NULLS = {"", "null", "none", "n/a", "na"}


def is_null(value: Any) -> bool:
    return value is None or str(value).strip().lower() in NULLS


def infer_physical_type(values: list[Any]) -> str:
    concrete = [str(value).strip() for value in values if not is_null(value)]
    if not concrete:
        return "String"
    lowered = {value.lower() for value in concrete}
    if lowered <= {"true", "false", "0", "1", "yes", "no"}:
        return "Boolean"
    try:
        for value in concrete:
            int(value)
        return "Integer"
    except ValueError:
        pass
    try:
        for value in concrete:
            Decimal(value)
        return "Decimal"
    except InvalidOperation:
        pass
    for format_name, result in (("%Y-%m-%d", "Date"), ("%Y-%m-%dT%H:%M:%S", "DateTime")):
        try:
            for value in concrete:
                datetime.strptime(value.rstrip("Z"), format_name)
            return result
        except ValueError:
            continue
    return "String"


def infer_semantic_type(column: str, values: list[Any]) -> str:
    name = column.casefold()
    if "email" in name:
        return "EMAIL"
    if name.endswith("_id") or name == "id":
        return "IDENTIFIER"
    if "date" in name or name.endswith("_at"):
        return "TEMPORAL"
    if any(token in name for token in ("amount", "price", "total", "spending")):
        return "MONETARY"
    if any(token in name for token in ("status", "state", "category")):
        return "CATEGORICAL"
    non_null = [str(value) for value in values if not is_null(value)]
    if non_null and all(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value) for value in non_null):
        return "EMAIL"
    return "UNKNOWN"


def profile_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[ColumnProfile]]:
    if not rows:
        raise ValueError("Profiling requires at least one row")
    columns = list(rows[0])
    schema = []
    profiles = []
    for column in columns:
        values = [row.get(column) for row in rows]
        null_count = sum(is_null(value) for value in values)
        concrete = [str(value) for value in values if not is_null(value)]
        counts = Counter(concrete)
        physical_type = infer_physical_type(values)
        semantic_type = infer_semantic_type(column, values)
        schema.append(
            {
                "column_name": column,
                "physical_type": physical_type,
                "nullable": null_count > 0,
                "semantic_type": semantic_type,
            }
        )
        profiles.append(
            ColumnProfile(
                column_name=column,
                physical_type=physical_type,
                row_count=len(rows),
                null_count=null_count,
                null_percentage=round(100 * null_count / len(rows), 2),
                distinct_count=len(counts),
                duplicate_count=sum(count - 1 for count in counts.values() if count > 1),
                min_value=min(concrete) if concrete else None,
                max_value=max(concrete) if concrete else None,
                sample_values=list(dict.fromkeys(concrete))[:5],
                semantic_type=semantic_type,
            )
        )
    return schema, profiles


def quality_summary(profiles: list[ColumnProfile]) -> dict[str, Any]:
    total_cells = sum(profile.row_count for profile in profiles) or 1
    nulls = sum(profile.null_count for profile in profiles)
    duplicates = sum(profile.duplicate_count for profile in profiles)
    completeness = round(100 * (1 - nulls / total_cells), 2)
    uniqueness = round(100 * (1 - duplicates / total_cells), 2)
    score = round(0.65 * completeness + 0.35 * uniqueness, 2)
    return {
        "score": score,
        "status": "PASS" if score >= 90 else "REVIEW" if score >= 70 else "FAIL",
        "dimensions": [
            {"name": "completeness", "score": completeness, "violation_count": nulls},
            {"name": "uniqueness", "score": uniqueness, "violation_count": duplicates},
        ],
    }
