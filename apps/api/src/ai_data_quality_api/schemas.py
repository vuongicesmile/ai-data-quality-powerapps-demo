"""Public command schemas for FastAPI and the Power Platform custom connector."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class IngestionCommand(BaseModel):
    force: bool = False
    run_id: str | None = None


class AssetSelectionCommand(BaseModel):
    asset_key: str


class RuleReviewCommand(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    actor: str
    parameters: dict[str, Any] | None = None


class ActorCommand(BaseModel):
    actor: str = "demo-user"


class MappingApprovalCommand(BaseModel):
    actor: str = "demo-user"
    mapping: dict[str, Any] | None = None


class ApprovalCommand(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    actor: str
    reason: str = ""


class GoldRecipeCommand(BaseModel):
    recipe_id: str | None = None
    target_asset: str
    source_asset: str
    joins: list[dict[str, Any]] = Field(default_factory=list)
    filters: list[dict[str, Any]] = Field(default_factory=list)
    dimensions: list[dict[str, Any]] = Field(default_factory=list)
    measures: list[dict[str, Any]] = Field(default_factory=list)
    actor: str


class GoldReviewCommand(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    actor: str


class GoldRunCommand(BaseModel):
    recipe_id: str
