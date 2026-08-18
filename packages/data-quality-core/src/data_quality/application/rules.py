"""Deterministic rule candidate generation and evidence-producing execution."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from data_quality.domain.models import ColumnProfile, RuleDefinition, RuleResult

from .profiling import is_null


def generate_rules(asset_key: str, profiles: list[ColumnProfile]) -> list[RuleDefinition]:
    rules = []
    for profile in profiles:
        if profile.null_count == 0:
            rules.append(
                RuleDefinition(
                    rule_id=f"rule_{uuid4().hex[:12]}",
                    asset_key=asset_key,
                    column_name=profile.column_name,
                    rule_type="NOT_NULL",
                    description=f"{profile.column_name} must not be blank",
                )
            )
        if profile.semantic_type == "IDENTIFIER" and profile.duplicate_count == 0:
            rules.append(
                RuleDefinition(
                    rule_id=f"rule_{uuid4().hex[:12]}",
                    asset_key=asset_key,
                    column_name=profile.column_name,
                    rule_type="UNIQUE",
                    description=f"{profile.column_name} must be unique",
                )
            )
        if profile.semantic_type == "EMAIL":
            rules.append(
                RuleDefinition(
                    rule_id=f"rule_{uuid4().hex[:12]}",
                    asset_key=asset_key,
                    column_name=profile.column_name,
                    rule_type="EMAIL",
                    description=f"{profile.column_name} must contain a valid email address",
                )
            )
    return rules


def execute_rules(
    asset_key: str, rows: list[dict[str, Any]], rules: list[RuleDefinition]
) -> list[RuleResult]:
    results = []
    for rule in rules:
        if rule.status != "APPROVED":
            continue
        evidence = []
        seen: set[str] = set()
        for index, row in enumerate(rows, start=1):
            value = row.get(rule.column_name or "")
            failed = False
            if rule.rule_type == "NOT_NULL":
                failed = is_null(value)
            elif rule.rule_type == "UNIQUE":
                normalized = str(value)
                failed = normalized in seen
                seen.add(normalized)
            elif rule.rule_type == "EMAIL" and not is_null(value):
                failed = re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(value)) is None
            if failed:
                evidence.append(
                    {
                        "row_number": index,
                        "column_name": rule.column_name,
                        "masked_value": mask_value(str(value), rule.column_name or ""),
                        "rule_id": rule.rule_id,
                    }
                )
        results.append(
            RuleResult(
                rule_id=rule.rule_id,
                asset_key=asset_key,
                status="FAIL" if evidence else "PASS",
                violation_count=len(evidence),
                evidence=evidence[:100],
            )
        )
    return results


def mask_value(value: str, column: str) -> str:
    if "email" in column.casefold() and "@" in value:
        local, domain = value.split("@", 1)
        return (local[:1] + "***@" + domain) if local else "***@" + domain
    if len(value) <= 4:
        return "***"
    return value[:2] + "***" + value[-2:]
