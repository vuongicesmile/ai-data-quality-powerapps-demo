"""Provider-neutral application API consumed by the Power Apps custom connector."""

from __future__ import annotations

from typing import Annotated, Any

from data_quality.application import GenericDatasetWorkflow, IngestionService
from data_quality.config import Settings
from fastapi import APIRouter, Depends, Query, status

from .dependencies import (
    get_ingestion_service,
    get_workflow,
    settings_dependency,
)
from .schemas import (
    ActorCommand,
    ApprovalCommand,
    AssetSelectionCommand,
    GoldRecipeCommand,
    GoldReviewCommand,
    GoldRunCommand,
    IngestionCommand,
    MappingApprovalCommand,
    RuleReviewCommand,
)

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])
WorkflowDep = Annotated[GenericDatasetWorkflow, Depends(get_workflow)]
IngestionDep = Annotated[IngestionService, Depends(get_ingestion_service)]
SettingsDep = Annotated[Settings, Depends(settings_dependency)]


@router.get("")
def list_datasets(workflow: WorkflowDep, settings: SettingsDep) -> list[dict[str, Any]]:
    return [workflow.overview(settings.dataset_key)]


@router.get("/{dataset_key}")
def get_dataset(dataset_key: str, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.overview(dataset_key)


@router.post("/{dataset_key}/ingestion-runs", status_code=status.HTTP_202_ACCEPTED)
def start_ingestion(
    dataset_key: str,
    command: IngestionCommand,
    workflow: WorkflowDep,
    ingestion: IngestionDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    del settings
    manifest = ingestion.run(dataset_key, force=command.force)
    result = workflow.sync_from_bronze(dataset_key)
    run_id = command.run_id or str(manifest["batch_id"])
    run = {
        "run_id": run_id,
        "status": "SUCCESS",
        "progress": 100,
        "manifest": manifest,
        "dataset": result["dataset"],
    }
    workflow.set_ingestion(dataset_key, run)
    return run


@router.get("/{dataset_key}/ingestion-runs/{run_id}")
def ingestion_status(
    dataset_key: str,
    run_id: str,
    workflow: WorkflowDep,
) -> dict[str, Any]:
    result = workflow.overview(dataset_key)["ingestion"]
    return {**result, "requested_run_id": run_id}


@router.post("/{dataset_key}/sync")
def sync_bronze(dataset_key: str, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.sync_from_bronze(dataset_key)


@router.get("/{dataset_key}/assets")
def list_assets(dataset_key: str, workflow: WorkflowDep) -> list[dict[str, Any]]:
    return workflow.list_assets(dataset_key)


@router.post("/{dataset_key}/assets/select")
def select_asset(
    dataset_key: str, command: AssetSelectionCommand, workflow: WorkflowDep
) -> dict[str, Any]:
    return workflow.select_asset(dataset_key, command.asset_key)


@router.post("/{dataset_key}/discover")
def discover(dataset_key: str, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.discover(dataset_key)


@router.post("/{dataset_key}/profile")
def profile(dataset_key: str, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.profile(dataset_key)


@router.get("/{dataset_key}/schema")
def schema(
    dataset_key: str, workflow: WorkflowDep, asset_key: str | None = Query(default=None)
) -> dict[str, Any]:
    return workflow.get_schema(dataset_key, asset_key)


@router.get("/{dataset_key}/profiles")
def profiles(
    dataset_key: str, workflow: WorkflowDep, asset_key: str | None = Query(default=None)
) -> dict[str, Any]:
    return workflow.get_profiles(dataset_key, asset_key)


@router.get("/{dataset_key}/rules")
def rules(
    dataset_key: str, workflow: WorkflowDep, asset_key: str | None = Query(default=None)
) -> dict[str, Any]:
    return workflow.list_rules(dataset_key, asset_key)


@router.post("/{dataset_key}/rules/approve-all")
def approve_rules(dataset_key: str, command: ActorCommand, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.approve_all_rules(dataset_key, actor=command.actor)


@router.post("/{dataset_key}/rules/{rule_id}/review")
def review_rule(
    dataset_key: str, rule_id: str, command: RuleReviewCommand, workflow: WorkflowDep
) -> dict[str, Any]:
    return workflow.review_rule(
        dataset_key,
        rule_id,
        decision=command.decision,
        actor=command.actor,
        parameters=command.parameters,
    )


@router.post("/{dataset_key}/rules/execute")
def execute_rules(dataset_key: str, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.run_rules(dataset_key)


@router.get("/{dataset_key}/evidence")
def evidence(
    dataset_key: str,
    workflow: WorkflowDep,
    asset_key: str,
    rule_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return workflow.evidence(dataset_key, asset_key=asset_key, rule_id=rule_id)


@router.get("/{dataset_key}/mappings/{asset_key}")
def mapping(dataset_key: str, asset_key: str, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.get_mapping(dataset_key, asset_key)


@router.post("/{dataset_key}/mappings/{asset_key}/approve")
def approve_mapping(
    dataset_key: str,
    asset_key: str,
    command: MappingApprovalCommand,
    workflow: WorkflowDep,
) -> dict[str, Any]:
    return workflow.approve_mapping(
        dataset_key, asset_key, actor=command.actor, payload=command.mapping
    )


@router.post("/{dataset_key}/mappings/approve-all")
def approve_all_mappings(
    dataset_key: str, command: ActorCommand, workflow: WorkflowDep
) -> dict[str, Any]:
    return workflow.approve_all_mappings(dataset_key, actor=command.actor)


@router.post("/{dataset_key}/approvals/{layer}")
def approve_layer(
    dataset_key: str, layer: str, command: ApprovalCommand, workflow: WorkflowDep
) -> dict[str, Any]:
    return workflow.approve_layer(
        dataset_key,
        layer,
        decision=command.decision,
        actor=command.actor,
        reason=command.reason,
    )


@router.post("/{dataset_key}/silver/run")
def run_silver(dataset_key: str, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.transform(dataset_key)


@router.get("/{dataset_key}/silver")
def get_silver(dataset_key: str, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.get_silver(dataset_key)


@router.post("/{dataset_key}/gold/recipes", status_code=status.HTTP_201_CREATED)
def create_gold_recipe(
    dataset_key: str, command: GoldRecipeCommand, workflow: WorkflowDep
) -> dict[str, Any]:
    return workflow.propose_gold_recipe(dataset_key, command.model_dump(exclude_none=True))


@router.get("/{dataset_key}/gold/recipes")
def list_gold_recipes(dataset_key: str, workflow: WorkflowDep) -> list[dict[str, Any]]:
    return workflow.list_gold_recipes(dataset_key)


@router.post("/{dataset_key}/gold/recipes/{recipe_id}/review")
def review_gold_recipe(
    dataset_key: str,
    recipe_id: str,
    command: GoldReviewCommand,
    workflow: WorkflowDep,
) -> dict[str, Any]:
    return workflow.review_gold_recipe(
        dataset_key, recipe_id, decision=command.decision, actor=command.actor
    )


@router.post("/{dataset_key}/gold/run")
def run_gold(dataset_key: str, command: GoldRunCommand, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.run_gold(dataset_key, command.recipe_id)


@router.get("/{dataset_key}/gold")
def get_gold(dataset_key: str, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.get_gold(dataset_key)


@router.get("/{dataset_key}/lineage")
def lineage(dataset_key: str, workflow: WorkflowDep) -> dict[str, Any]:
    return workflow.lineage(dataset_key)
