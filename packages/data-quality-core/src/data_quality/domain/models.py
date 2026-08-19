"""Serializable domain state for the governed Generic Dataset workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class SourceAsset(BaseModel):
    provider: str
    asset_key: str
    file_name: str
    source_id: str
    source_path: str
    source_version: str
    size_bytes: int = Field(ge=0)
    last_modified_at: str
    source_web_url: str = ""


class BronzeAsset(SourceAsset):
    bronze_key: str
    content_hash: str
    bronze_item_id: str = ""
    bronze_etag: str = ""
    bronze_web_url: str = ""
    row_count: int = Field(default=0, ge=0)
    columns: list[str] = Field(default_factory=list)
    source_list_id: str = ""
    source_list_name: str = ""
    captured_at: str = ""


class ColumnProfile(BaseModel):
    column_name: str
    physical_type: str
    row_count: int
    null_count: int
    null_percentage: float
    distinct_count: int
    duplicate_count: int
    min_value: str | None = None
    max_value: str | None = None
    sample_values: list[str] = Field(default_factory=list)
    semantic_type: str = "UNKNOWN"


class RuleDefinition(BaseModel):
    rule_id: str
    asset_key: str
    column_name: str | None = None
    rule_type: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: Literal["PROPOSED", "APPROVED", "REJECTED"] = "PROPOSED"
    source: Literal["DETERMINISTIC", "LLM"] = "DETERMINISTIC"
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    etag: str | None = Field(default=None, exclude=True)


class RuleResult(BaseModel):
    rule_id: str
    asset_key: str
    status: Literal["PASS", "FAIL"]
    violation_count: int
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class MappingColumn(BaseModel):
    source: str
    target: str
    type: Literal["String", "Integer", "Decimal", "Date", "DateTime", "Boolean"]
    nullable: bool = True


class AssetMapping(BaseModel):
    asset_key: str
    version: int = 1
    status: Literal["DRAFT", "APPROVED"] = "DRAFT"
    columns: list[MappingColumn]
    business_key: list[str] = Field(default_factory=list)
    target_table: str
    approved_by: str | None = None
    approved_at: str | None = None
    etag: str | None = Field(default=None, exclude=True)


class ApprovalEvent(BaseModel):
    approval_id: str
    layer: Literal["BRONZE", "SILVER", "GOLD"]
    decision: Literal["APPROVED", "REJECTED"]
    actor: str
    reason: str = ""
    recorded_at: str = Field(default_factory=utc_now)
    etag: str | None = Field(default=None, exclude=True)


class GoldRecipe(BaseModel):
    recipe_id: str
    version: int = 1
    status: Literal["DRAFT", "APPROVED", "REJECTED"] = "DRAFT"
    target_asset: str
    source_asset: str
    joins: list[dict[str, Any]] = Field(default_factory=list)
    filters: list[dict[str, Any]] = Field(default_factory=list)
    dimensions: list[dict[str, Any]] = Field(default_factory=list)
    measures: list[dict[str, Any]] = Field(default_factory=list)
    actor: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    etag: str | None = Field(default=None, exclude=True)


class ActivityEvent(BaseModel):
    event_id: str
    action: str
    status: str
    actor: str = "system"
    detail: str = ""
    recorded_at: str = Field(default_factory=utc_now)


class WorkflowState(BaseModel):
    dataset_key: str
    dataset_id: str = "timerapp.projects"
    dataset_name: str = "TimerApp Data Quality"
    provider: str = "sharepoint-list"
    revision: int = 0
    status: str = "EMPTY"
    selected_asset_key: str | None = None
    bronze_manifest: dict[str, Any] = Field(default_factory=dict)
    assets: dict[str, BronzeAsset] = Field(default_factory=dict)
    rows: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    schemas: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    profiles: dict[str, list[ColumnProfile]] = Field(default_factory=dict)
    quality: dict[str, dict[str, Any]] = Field(default_factory=dict)
    rules: dict[str, list[RuleDefinition]] = Field(default_factory=dict)
    rule_results: dict[str, list[RuleResult]] = Field(default_factory=dict)
    mappings: dict[str, AssetMapping] = Field(default_factory=dict)
    approvals: dict[str, ApprovalEvent] = Field(default_factory=dict)
    silver: dict[str, dict[str, Any]] = Field(default_factory=dict)
    gold_recipes: dict[str, GoldRecipe] = Field(default_factory=dict)
    gold: dict[str, Any] = Field(default_factory=dict)
    activity: list[ActivityEvent] = Field(default_factory=list)
    ingestion: dict[str, Any] = Field(default_factory=lambda: {"status": "IDLE", "progress": 0})
    lifecycle: dict[str, bool] = Field(
        default_factory=lambda: {
            "ingested": False,
            "discovered": False,
            "profiled": False,
            "bronze_approved": False,
            "transformed": False,
            "silver_approved": False,
            "gold_published": False,
            "gold_approved": False,
        }
    )
    updated_at: str = Field(default_factory=utc_now)

    def overview(self) -> dict[str, Any]:
        completed = sum(self.lifecycle.values())
        lifecycle = {
            **self.lifecycle,
            "completed_steps": completed,
            "total_steps": len(self.lifecycle),
            "progress": round(100 * completed / len(self.lifecycle)),
            "current_step": next(
                (name for name, done in self.lifecycle.items() if not done), "completed"
            ),
        }
        return {
            "dataset_key": self.dataset_key,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "provider": self.provider,
            "revision": self.revision,
            "status": self.status,
            "selected_asset_key": self.selected_asset_key,
            "assets": [asset.model_dump() for asset in self.assets.values()],
            "manifest": self.bronze_manifest,
            "lifecycle": lifecycle,
            "ingestion": self.ingestion,
            "approvals": {key: value.model_dump() for key, value in self.approvals.items()},
            "silver": self.silver,
            "gold": self.gold,
            "updated_at": self.updated_at,
        }
