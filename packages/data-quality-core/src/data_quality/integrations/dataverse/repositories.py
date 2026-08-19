"""Normalized Dataverse repositories for workflow, Silver, and Gold records."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from data_quality.domain.models import (
    ActivityEvent,
    ApprovalEvent,
    AssetMapping,
    BronzeAsset,
    ColumnProfile,
    GoldRecipe,
    RuleDefinition,
    RuleResult,
    WorkflowState,
)

from .client import DataverseClient

LIFECYCLE = {
    "EMPTY": 100000000,
    "INGESTED": 100000001,
    "DISCOVERED": 100000002,
    "PROFILED": 100000003,
    "SILVER_PUBLISHED": 100000004,
    "GOLD_PUBLISHED": 100000005,
}
RUN_STATUS = {"QUEUED": 100000000, "RUNNING": 100000001, "SUCCESS": 100000002, "FAILED": 100000003}
REVIEW_STATUS = {"PENDING": 100000000, "PROPOSED": 100000001, "APPROVED": 100000002, "REJECTED": 100000003, "DRAFT": 100000000}
LAYERS = {"BRONZE": 100000000, "SILVER": 100000001, "GOLD": 100000002}
RESULT_STATUS = {"PASS": 100000000, "FAIL": 100000001}


def decode(mapping: dict[str, int], value: Any, default: str) -> str:
    return next((name for name, code in mapping.items() if code == value), default)


def dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, default=str)


def loads(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(str(value))
    except (TypeError, ValueError):
        return default


class DataverseStateRepository:
    def __init__(self, client: DataverseClient) -> None:
        self.client = client

    def load(self, dataset_key: str) -> WorkflowState | None:
        escaped = self.client.escape(dataset_key)
        datasets = self.client.query(
            "dq_datasets",
            select=[
                "dq_datasetkey", "dq_name", "dq_status", "dq_selectedassetkey",
                "dq_revision", "dq_sourceprovider", "dq_manifestjson", "dq_qualityjson",
                "dq_silverjson", "dq_goldjson", "dq_ingested", "dq_discovered",
                "dq_profiled", "dq_bronzeapproved", "dq_transformed", "dq_silverapproved",
                "dq_goldpublished", "dq_goldapproved", "dq_updatedat",
            ],
            filter=f"dq_datasetkey eq '{escaped}'",
            top=1,
        )
        if not datasets:
            return None
        row = datasets[0]
        manifest = loads(row.get("dq_manifestjson"), {})
        batch_key = str(manifest.get("batch_id", ""))
        state = WorkflowState(
            dataset_key=dataset_key,
            dataset_name=str(row.get("dq_name") or dataset_key),
            provider=str(row.get("dq_sourceprovider") or "sharepoint"),
            revision=int(row.get("dq_revision") or 0),
            status=decode(LIFECYCLE, row.get("dq_status"), "EMPTY"),
            selected_asset_key=row.get("dq_selectedassetkey"),
            bronze_manifest=manifest,
            quality=loads(row.get("dq_qualityjson"), {}),
            silver=loads(row.get("dq_silverjson"), {}),
            gold=loads(row.get("dq_goldjson"), {}),
            lifecycle={
                "ingested": bool(row.get("dq_ingested")),
                "discovered": bool(row.get("dq_discovered")),
                "profiled": bool(row.get("dq_profiled")),
                "bronze_approved": bool(row.get("dq_bronzeapproved")),
                "transformed": bool(row.get("dq_transformed")),
                "silver_approved": bool(row.get("dq_silverapproved")),
                "gold_published": bool(row.get("dq_goldpublished")),
                "gold_approved": bool(row.get("dq_goldapproved")),
            },
            updated_at=str(row.get("dq_updatedat") or ""),
        )
        if batch_key:
            self._load_batch(state, batch_key)
        self._load_governance(state)
        return state

    def save(self, state: WorkflowState) -> None:
        lifecycle = state.lifecycle
        self.client.upsert(
            "dq_datasets",
            {"dq_datasetkey": state.dataset_key},
            {
                "dq_name": state.dataset_name,
                "dq_datasetkey": state.dataset_key,
                "dq_status": LIFECYCLE.get(state.status, LIFECYCLE["EMPTY"]),
                "dq_selectedassetkey": state.selected_asset_key,
                "dq_revision": state.revision,
                "dq_sourceprovider": state.provider,
                "dq_manifestjson": dumps(state.bronze_manifest),
                "dq_qualityjson": dumps(state.quality),
                "dq_silverjson": dumps(state.silver),
                "dq_goldjson": dumps(state.gold),
                "dq_ingested": lifecycle["ingested"],
                "dq_discovered": lifecycle["discovered"],
                "dq_profiled": lifecycle["profiled"],
                "dq_bronzeapproved": lifecycle["bronze_approved"],
                "dq_transformed": lifecycle["transformed"],
                "dq_silverapproved": lifecycle["silver_approved"],
                "dq_goldpublished": lifecycle["gold_published"],
                "dq_goldapproved": lifecycle["gold_approved"],
                "dq_updatedat": state.updated_at,
            },
        )
        self._save_batch(state)
        self._save_governance(state)

    def _load_batch(self, state: WorkflowState, batch_key: str) -> None:
        escaped = self.client.escape(batch_key)
        snapshots = {
            str(row.get("dq_assetkey")): row
            for row in self.client.query(
                "dq_bronzesnapshots",
                select=["dq_assetkey", "dq_driveitemid", "dq_etag", "dq_weburl", "dq_immutablepath"],
                filter=f"dq_batchkey eq '{escaped}'",
            )
        }
        rows = self.client.query(
            "dq_assets",
            select=[
                "dq_assetkey", "dq_filename", "dq_sourceitemid", "dq_sourceetag",
                "dq_sourcepath", "dq_rowcount", "dq_contenthash", "dq_columnsjson",
            ],
            filter=f"dq_batchkey eq '{escaped}'",
        )
        for row in rows:
            asset_key = str(row["dq_assetkey"])
            bronze = snapshots.get(asset_key, {})
            state.assets[asset_key] = BronzeAsset(
                provider=state.provider,
                asset_key=asset_key,
                file_name=str(row.get("dq_filename") or asset_key + ".csv"),
                source_id=str(row.get("dq_sourceitemid") or ""),
                source_path=str(row.get("dq_sourcepath") or ""),
                source_version=str(row.get("dq_sourceetag") or ""),
                size_bytes=0,
                last_modified_at="",
                bronze_key=str(bronze.get("dq_immutablepath") or ""),
                bronze_item_id=str(bronze.get("dq_driveitemid") or ""),
                bronze_etag=str(bronze.get("dq_etag") or ""),
                bronze_web_url=str(bronze.get("dq_weburl") or ""),
                content_hash=str(row.get("dq_contenthash") or ""),
                row_count=int(row.get("dq_rowcount") or 0),
                columns=loads(row.get("dq_columnsjson"), []),
            )

    def _load_governance(self, state: WorkflowState) -> None:
        dataset = self.client.escape(state.dataset_key)
        batch = self.client.escape(str(state.bronze_manifest.get("batch_id", "")))
        batch_filter = f"dq_batchkey eq '{batch}'" if batch else "dq_batchkey eq ''"
        for row in self.client.query(
            "dq_columnprofiles",
            select=[
                "dq_assetkey", "dq_columnname", "dq_physicaltype", "dq_semantictype",
                "dq_rowcount", "dq_nullcount", "dq_nullpercentage", "dq_distinctcount",
                "dq_duplicatecount", "dq_minvalue", "dq_maxvalue", "dq_samplesjson",
            ],
            filter=batch_filter,
        ):
            key = str(row["dq_assetkey"])
            profile = ColumnProfile(
                column_name=str(row["dq_columnname"]),
                physical_type=str(row.get("dq_physicaltype") or "String"),
                semantic_type=str(row.get("dq_semantictype") or "UNKNOWN"),
                row_count=int(row.get("dq_rowcount") or 0),
                null_count=int(row.get("dq_nullcount") or 0),
                null_percentage=float(row.get("dq_nullpercentage") or 0),
                distinct_count=int(row.get("dq_distinctcount") or 0),
                duplicate_count=int(row.get("dq_duplicatecount") or 0),
                min_value=row.get("dq_minvalue"),
                max_value=row.get("dq_maxvalue"),
                sample_values=loads(row.get("dq_samplesjson"), []),
            )
            state.profiles.setdefault(key, []).append(profile)
            state.schemas.setdefault(key, []).append(
                {
                    "column_name": profile.column_name,
                    "physical_type": profile.physical_type,
                    "nullable": profile.null_count > 0,
                    "semantic_type": profile.semantic_type,
                }
            )
        for row in self.client.query(
            "dq_rules",
            select=[
                "dq_rulekey", "dq_assetkey", "dq_columnname", "dq_ruletype",
                "dq_description", "dq_parametersjson", "dq_status", "dq_source",
                "dq_reviewedby", "dq_reviewedat",
            ],
            filter=f"dq_datasetkey eq '{dataset}' and {batch_filter}",
        ):
            rule = RuleDefinition(
                rule_id=str(row["dq_rulekey"]),
                asset_key=str(row.get("dq_assetkey") or ""),
                column_name=row.get("dq_columnname"),
                rule_type=str(row.get("dq_ruletype") or ""),
                description=str(row.get("dq_description") or ""),
                parameters=loads(row.get("dq_parametersjson"), {}),
                status=decode(REVIEW_STATUS, row.get("dq_status"), "PROPOSED"),
                source=str(row.get("dq_source") or "DETERMINISTIC"),
                reviewed_by=row.get("dq_reviewedby"),
                reviewed_at=row.get("dq_reviewedat"),
                etag=row.get("@odata.etag"),
            )
            state.rules.setdefault(rule.asset_key, []).append(rule)
        evidence_rows = self.client.query(
            "dq_evidences",
            select=["dq_rulekey", "dq_assetkey", "dq_sourcerownumber", "dq_detailjson"],
            filter=batch_filter,
        )
        evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in evidence_rows:
            evidence[str(row["dq_rulekey"])].append(loads(row.get("dq_detailjson"), {}))
        for row in self.client.query(
            "dq_ruleresults",
            select=["dq_rulekey", "dq_assetkey", "dq_status", "dq_violationcount"],
            filter=batch_filter,
        ):
            result = RuleResult(
                rule_id=str(row["dq_rulekey"]),
                asset_key=str(row.get("dq_assetkey") or ""),
                status=decode(RESULT_STATUS, row.get("dq_status"), "PASS"),
                violation_count=int(row.get("dq_violationcount") or 0),
                evidence=evidence.get(str(row["dq_rulekey"]), []),
            )
            state.rule_results.setdefault(result.asset_key, []).append(result)
        for row in self.client.query(
            "dq_mappings",
            select=["dq_assetkey", "dq_mappingjson"],
            filter=f"dq_datasetkey eq '{dataset}'",
            orderby="dq_version desc",
        ):
            key = str(row["dq_assetkey"])
            if key not in state.mappings:
                state.mappings[key] = AssetMapping.model_validate(
                    {**loads(row["dq_mappingjson"], {}), "etag": row.get("@odata.etag")}
                )
        for row in self.client.query(
            "dq_approvals",
            select=["dq_approvalkey", "dq_layer", "dq_decision", "dq_actor", "dq_reason", "dq_recordedat"],
            filter=f"dq_datasetkey eq '{dataset}'",
            orderby="dq_recordedat desc",
        ):
            layer = decode(LAYERS, row.get("dq_layer"), "BRONZE")
            if layer not in state.approvals:
                state.approvals[layer] = ApprovalEvent(
                    approval_id=str(row["dq_approvalkey"]),
                    layer=layer,
                    decision=decode(REVIEW_STATUS, row.get("dq_decision"), "REJECTED"),
                    actor=str(row.get("dq_actor") or ""),
                    reason=str(row.get("dq_reason") or ""),
                    recorded_at=str(row.get("dq_recordedat") or ""),
                    etag=row.get("@odata.etag"),
                )
        for row in self.client.query(
            "dq_goldrecipes",
            select=["dq_recipekey", "dq_recipejson"],
            filter=f"dq_datasetkey eq '{dataset}'",
            orderby="dq_version desc",
        ):
            key = str(row["dq_recipekey"])
            if key not in state.gold_recipes:
                state.gold_recipes[key] = GoldRecipe.model_validate(
                    {**loads(row["dq_recipejson"], {}), "etag": row.get("@odata.etag")}
                )
        for row in self.client.query(
            "dq_activities",
            select=["dq_activitykey", "dq_action", "dq_status", "dq_actor", "dq_detail", "dq_recordedat"],
            filter=f"dq_datasetkey eq '{dataset}'",
            orderby="dq_recordedat asc",
            top=100,
        ):
            state.activity.append(
                ActivityEvent(
                    event_id=str(row["dq_activitykey"]),
                    action=str(row.get("dq_action") or ""),
                    status=str(row.get("dq_status") or ""),
                    actor=str(row.get("dq_actor") or "system"),
                    detail=str(row.get("dq_detail") or ""),
                    recorded_at=str(row.get("dq_recordedat") or ""),
                )
            )
        runs = self.client.query(
            "dq_ingestionruns",
            select=["dq_name", "dq_status", "dq_progress", "dq_startedat", "dq_completedat"],
            filter=f"dq_datasetkey eq '{dataset}'",
            orderby="createdon desc",
            top=1,
        )
        if runs:
            state.ingestion = {
                "run_id": runs[0].get("dq_name"),
                "status": decode(RUN_STATUS, runs[0].get("dq_status"), "QUEUED"),
                "progress": int(runs[0].get("dq_progress") or 0),
                "started_at": runs[0].get("dq_startedat"),
                "completed_at": runs[0].get("dq_completedat"),
            }

    def _save_batch(self, state: WorkflowState) -> None:
        batch_key = str(state.bronze_manifest.get("batch_id", ""))
        if not batch_key:
            return
        self.client.upsert(
            "dq_batches",
            {"dq_name": batch_key},
            {
                "dq_name": batch_key,
                "dq_datasetkey": state.dataset_key,
                "dq_dataset@odata.bind": self._bind("dq_datasets", {"dq_datasetkey": state.dataset_key}),
                "dq_sourceversionhash": self._hash(
                    {item.source_id: item.source_version for item in state.assets.values()}
                ),
                "dq_manifesturl": state.bronze_manifest.get("manifest_web_url"),
                "dq_manifestitemid": state.bronze_manifest.get("manifest_item_id"),
                "dq_manifestetag": state.bronze_manifest.get("manifest_etag"),
                "dq_publishedat": state.bronze_manifest.get("published_at"),
                "dq_status": RUN_STATUS["SUCCESS"],
            },
        )
        for asset in state.assets.values():
            self.client.upsert(
                "dq_assets",
                {"dq_batchkey": batch_key, "dq_assetkey": asset.asset_key},
                {
                    "dq_name": f"{batch_key}:{asset.asset_key}",
                    "dq_batchkey": batch_key,
                    "dq_batch@odata.bind": self._bind("dq_batches", {"dq_name": batch_key}),
                    "dq_assetkey": asset.asset_key,
                    "dq_filename": asset.file_name,
                    "dq_sourceitemid": asset.source_id,
                    "dq_sourceetag": asset.source_version,
                    "dq_sourcepath": asset.source_path,
                    "dq_rowcount": asset.row_count,
                    "dq_columncount": len(asset.columns),
                    "dq_contenthash": asset.content_hash,
                    "dq_columnsjson": dumps(asset.columns),
                },
            )
            self.client.upsert(
                "dq_bronzesnapshots",
                {"dq_batchkey": batch_key, "dq_assetkey": asset.asset_key},
                {
                    "dq_name": f"{batch_key}:{asset.asset_key}",
                    "dq_batchkey": batch_key,
                    "dq_asset@odata.bind": self._bind(
                        "dq_assets", {"dq_batchkey": batch_key, "dq_assetkey": asset.asset_key}
                    ),
                    "dq_assetkey": asset.asset_key,
                    "dq_driveitemid": asset.bronze_item_id,
                    "dq_etag": asset.bronze_etag,
                    "dq_weburl": asset.bronze_web_url,
                    "dq_contenthash": asset.content_hash,
                    "dq_sizebytes": asset.size_bytes,
                    "dq_immutablepath": asset.bronze_key,
                },
            )

    def _save_governance(self, state: WorkflowState) -> None:
        batch_key = str(state.bronze_manifest.get("batch_id", ""))
        for asset_key, profiles in state.profiles.items():
            for profile in profiles:
                self.client.upsert(
                    "dq_columnprofiles",
                    {"dq_batchkey": batch_key, "dq_assetkey": asset_key, "dq_columnname": profile.column_name},
                    {
                        "dq_name": f"{asset_key}.{profile.column_name}",
                        "dq_datasetkey": state.dataset_key,
                        "dq_batchkey": batch_key,
                        "dq_assetkey": asset_key,
                        "dq_columnname": profile.column_name,
                        "dq_physicaltype": profile.physical_type,
                        "dq_semantictype": profile.semantic_type,
                        "dq_rowcount": profile.row_count,
                        "dq_nullcount": profile.null_count,
                        "dq_nullpercentage": profile.null_percentage,
                        "dq_distinctcount": profile.distinct_count,
                        "dq_duplicatecount": profile.duplicate_count,
                        "dq_minvalue": profile.min_value,
                        "dq_maxvalue": profile.max_value,
                        "dq_samplesjson": dumps(profile.sample_values),
                    },
                )
        for rules in state.rules.values():
            for rule in rules:
                self.client.upsert(
                    "dq_rules",
                    {"dq_rulekey": rule.rule_id},
                    {
                        "dq_name": rule.description[:100], "dq_rulekey": rule.rule_id,
                        "dq_datasetkey": state.dataset_key, "dq_batchkey": batch_key,
                        "dq_assetkey": rule.asset_key, "dq_columnname": rule.column_name,
                        "dq_ruletype": rule.rule_type, "dq_description": rule.description,
                        "dq_parametersjson": dumps(rule.parameters),
                        "dq_status": REVIEW_STATUS[rule.status], "dq_source": rule.source,
                        "dq_reviewedby": rule.reviewed_by, "dq_reviewedat": rule.reviewed_at,
                    },
                    etag=rule.etag,
                )
        for results in state.rule_results.values():
            for result in results:
                self.client.upsert(
                    "dq_ruleresults",
                    {"dq_batchkey": batch_key, "dq_rulekey": result.rule_id},
                    {
                        "dq_name": f"{batch_key}:{result.rule_id}", "dq_batchkey": batch_key,
                        "dq_rulekey": result.rule_id, "dq_assetkey": result.asset_key,
                        "dq_status": RESULT_STATUS[result.status],
                        "dq_violationcount": result.violation_count,
                    },
                )
                for index, item in enumerate(result.evidence[:100], start=1):
                    evidence_key = self._hash({"rule": result.rule_id, "index": index, "item": item})
                    self.client.upsert(
                        "dq_evidences",
                        {"dq_batchkey": batch_key, "dq_rulekey": result.rule_id, "dq_evidencekey": evidence_key},
                        {
                            "dq_name": f"{result.rule_id}:{index}", "dq_batchkey": batch_key,
                            "dq_rulekey": result.rule_id, "dq_evidencekey": evidence_key,
                            "dq_assetkey": result.asset_key,
                            "dq_sourcerownumber": item.get("row_number", index),
                            "dq_maskedvalue": str(item.get("masked_value", "")),
                            "dq_detailjson": dumps(item),
                        },
                    )
        for mapping in state.mappings.values():
            self.client.upsert(
                "dq_mappings",
                {"dq_datasetkey": state.dataset_key, "dq_assetkey": mapping.asset_key, "dq_version": mapping.version},
                {
                    "dq_name": f"{mapping.asset_key} v{mapping.version}",
                    "dq_datasetkey": state.dataset_key, "dq_assetkey": mapping.asset_key,
                    "dq_version": mapping.version, "dq_status": REVIEW_STATUS[mapping.status],
                    "dq_mappingjson": dumps(mapping.model_dump()),
                    "dq_approvedby": mapping.approved_by, "dq_approvedat": mapping.approved_at,
                },
                etag=mapping.etag,
            )
        for approval in state.approvals.values():
            self.client.upsert(
                "dq_approvals", {"dq_approvalkey": approval.approval_id},
                {
                    "dq_name": f"{approval.layer} {approval.decision}",
                    "dq_approvalkey": approval.approval_id, "dq_datasetkey": state.dataset_key,
                    "dq_batchkey": batch_key, "dq_layer": LAYERS[approval.layer],
                    "dq_decision": REVIEW_STATUS[approval.decision], "dq_actor": approval.actor,
                    "dq_reason": approval.reason, "dq_recordedat": approval.recorded_at,
                },
                etag=approval.etag,
            )
        for recipe in state.gold_recipes.values():
            self.client.upsert(
                "dq_goldrecipes",
                {"dq_datasetkey": state.dataset_key, "dq_recipekey": recipe.recipe_id, "dq_version": recipe.version},
                {
                    "dq_name": f"{recipe.recipe_id} v{recipe.version}",
                    "dq_datasetkey": state.dataset_key, "dq_recipekey": recipe.recipe_id,
                    "dq_version": recipe.version, "dq_status": REVIEW_STATUS[recipe.status],
                    "dq_recipejson": dumps(recipe.model_dump()),
                    "dq_reviewedby": recipe.reviewed_by, "dq_reviewedat": recipe.reviewed_at,
                },
                etag=recipe.etag,
            )
        for event in state.activity[-100:]:
            self.client.upsert(
                "dq_activities", {"dq_activitykey": event.event_id},
                {
                    "dq_name": event.action, "dq_activitykey": event.event_id,
                    "dq_datasetkey": state.dataset_key, "dq_action": event.action,
                    "dq_status": event.status, "dq_actor": event.actor,
                    "dq_detail": event.detail, "dq_recordedat": event.recorded_at,
                },
            )
        run_id = str(state.ingestion.get("run_id") or state.ingestion.get("batch_id") or "")
        if run_id:
            status = str(state.ingestion.get("status") or "QUEUED").upper()
            self.client.upsert(
                "dq_ingestionruns", {"dq_name": run_id},
                {
                    "dq_name": run_id, "dq_datasetkey": state.dataset_key,
                    "dq_dataset@odata.bind": self._bind(
                        "dq_datasets", {"dq_datasetkey": state.dataset_key}
                    ),
                    "dq_status": RUN_STATUS.get(status, RUN_STATUS["QUEUED"]),
                    "dq_progress": int(state.ingestion.get("progress") or 0),
                    "dq_startedat": state.ingestion.get("started_at"),
                    "dq_completedat": state.ingestion.get("completed_at"),
                },
            )

    @staticmethod
    def _hash(value: Any) -> str:
        return hashlib.sha256(dumps(value).encode()).hexdigest()

    @staticmethod
    def _bind(entity_set: str, key: dict[str, Any]) -> str:
        expression = ",".join(
            f"{name}='{str(value).replace(chr(39), chr(39) * 2)}'"
            for name, value in key.items()
        )
        return f"/{entity_set}({expression})"


class DataverseWarehouseRepository:
    def __init__(self, client: DataverseClient) -> None:
        self.client = client

    def publish_silver(
        self, *, dataset_id: str, asset_key: str, mapping: dict[str, Any],
        rows: list[dict[str, Any]], rejected_rows: list[dict[str, Any]], batch_id: str,
    ) -> dict[str, Any]:
        published = []
        for row in rows:
            row_hash = self._hash(row)
            self.client.upsert(
                "dq_silverrows",
                {"dq_batchkey": batch_id, "dq_assetkey": asset_key, "dq_rowhash": row_hash},
                {
                    "dq_name": f"{asset_key}:{row.get('_source_row_number', 0)}",
                    "dq_datasetkey": dataset_id, "dq_batchkey": batch_id,
                    "dq_assetkey": asset_key,
                    "dq_sourcerownumber": int(row.get("_source_row_number", 0)),
                    "dq_rowhash": row_hash, "dq_validationstatus": RESULT_STATUS["PASS"],
                    "dq_payloadjson": dumps(row), "dq_rejectionjson": "[]",
                },
            )
            published.append(row_hash)
        for rejection in rejected_rows:
            row_hash = self._hash(rejection)
            self.client.upsert(
                "dq_silverrows",
                {"dq_batchkey": batch_id, "dq_assetkey": asset_key, "dq_rowhash": row_hash},
                {
                    "dq_name": f"{asset_key}:rejected:{rejection.get('row_number', 0)}",
                    "dq_datasetkey": dataset_id, "dq_batchkey": batch_id,
                    "dq_assetkey": asset_key,
                    "dq_sourcerownumber": int(rejection.get("row_number", 0)),
                    "dq_rowhash": row_hash, "dq_validationstatus": RESULT_STATUS["FAIL"],
                    "dq_payloadjson": "{}", "dq_rejectionjson": dumps(rejection),
                },
            )
        return {
            "provider": "dataverse", "entity_set": "dq_silverrows",
            "asset_key": asset_key, "row_count": len(rows),
            "rejected_row_count": len(rejected_rows),
            "snapshot_hash": self._hash(published), "mapping_version": mapping.get("version", 1),
        }

    def publish_gold(
        self, *, dataset_id: str, recipe: dict[str, Any],
        silver: dict[str, dict[str, Any]], batch_id: str,
    ) -> dict[str, Any]:
        source_asset = str(recipe["source_asset"])
        escaped_batch = self.client.escape(batch_id)
        required_assets = {source_asset} | {
            str(join["right_asset"]) for join in recipe.get("joins", [])
        }
        asset_rows: dict[str, list[dict[str, Any]]] = {}
        for asset in required_assets:
            if asset not in silver:
                raise ValueError(f"Silver source is not published: {asset}")
            escaped_asset = self.client.escape(asset)
            asset_rows[asset] = [
                loads(row.get("dq_payloadjson"), {})
                for row in self.client.query(
                    "dq_silverrows", select=["dq_payloadjson"],
                    filter=(
                        f"dq_batchkey eq '{escaped_batch}' and dq_assetkey eq '{escaped_asset}' "
                        f"and dq_validationstatus eq {RESULT_STATUS['PASS']}"
                    ),
                )
            ]
        joined = self._join_rows(source_asset, asset_rows, recipe.get("joins", []))
        flattened = [self._flatten(row) for row in joined]
        filtered = [row for row in flattened if self._matches_filters(row, recipe.get("filters", []))]
        results = self._aggregate(filtered, recipe)
        hashes = []
        for index, result in enumerate(results, start=1):
            row_hash = self._hash(result)
            hashes.append(row_hash)
            self.client.upsert(
                "dq_goldresults",
                {"dq_batchkey": batch_id, "dq_recipekey": recipe["recipe_id"], "dq_rowhash": row_hash},
                {
                    "dq_name": f"{recipe['recipe_id']}:{index}",
                    "dq_datasetkey": dataset_id, "dq_batchkey": batch_id,
                    "dq_recipekey": recipe["recipe_id"], "dq_recipeversion": recipe["version"],
                    "dq_rowhash": row_hash,
                    "dq_dimensionsjson": dumps(result.get("dimensions", {})),
                    "dq_measuresjson": dumps(result.get("measures", {})),
                    "dq_reconciliationstatus": RESULT_STATUS["PASS"],
                },
            )
        return {
            "provider": "dataverse", "entity_set": "dq_goldresults",
            "recipe_id": recipe["recipe_id"], "recipe_version": recipe["version"],
            "row_count": len(results), "snapshot_hash": self._hash(hashes),
            "reconciliation": "PASS",
        }

    @staticmethod
    def _join_rows(
        source_asset: str,
        assets: dict[str, list[dict[str, Any]]],
        joins: list[dict[str, Any]],
    ) -> list[dict[str, dict[str, Any]]]:
        combined = [{source_asset: row} for row in assets[source_asset]]
        for join in joins:
            right_asset = str(join["right_asset"])
            join_type = str(join.get("join_type", "LEFT")).upper()
            if join_type not in {"INNER", "LEFT", "RIGHT", "FULL"}:
                raise ValueError(f"Unsupported Gold join type: {join_type}")
            right_rows = assets[right_asset]
            matched_right: set[int] = set()
            next_rows: list[dict[str, dict[str, Any]]] = []
            for combined_row in combined:
                left_value = DataverseWarehouseRepository._nested_value(
                    combined_row, str(join["left"])
                )
                matches = [
                    (index, row)
                    for index, row in enumerate(right_rows)
                    if left_value
                    == DataverseWarehouseRepository._nested_value(
                        {right_asset: row}, str(join["right"])
                    )
                ]
                if matches:
                    for index, right_row in matches:
                        matched_right.add(index)
                        next_rows.append({**combined_row, right_asset: right_row})
                elif join_type in {"LEFT", "FULL"}:
                    next_rows.append({**combined_row, right_asset: {}})
            if join_type in {"RIGHT", "FULL"}:
                for index, right_row in enumerate(right_rows):
                    if index not in matched_right:
                        next_rows.append({source_asset: {}, right_asset: right_row})
            combined = next_rows
        return combined

    @staticmethod
    def _nested_value(row: dict[str, dict[str, Any]], reference: str) -> Any:
        asset, column = reference.split(".", 1)
        return row.get(asset, {}).get(column)

    @staticmethod
    def _flatten(row: dict[str, dict[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for asset, payload in row.items():
            for column, value in payload.items():
                result[f"{asset}.{column}"] = value
                result.setdefault(column, value)
        return result

    @staticmethod
    def _matches_filters(row: dict[str, Any], filters: list[dict[str, Any]]) -> bool:
        operators = {
            "eq": lambda left, right: left == right,
            "neq": lambda left, right: left != right,
            "gt": lambda left, right: left is not None and left > right,
            "gte": lambda left, right: left is not None and left >= right,
            "lt": lambda left, right: left is not None and left < right,
            "lte": lambda left, right: left is not None and left <= right,
            "in": lambda left, right: left in right,
        }
        for item in filters:
            operator = str(item["operator"])
            if operator not in operators:
                raise ValueError(f"Unsupported Gold filter: {operator}")
            if not operators[operator](row.get(str(item["column"])), item.get("value")):
                return False
        return True

    @staticmethod
    def _aggregate(rows: list[dict[str, Any]], recipe: dict[str, Any]) -> list[dict[str, Any]]:
        dimensions = recipe.get("dimensions", [])
        measures = recipe.get("measures", [])
        if not dimensions and not measures:
            return [{"dimensions": row, "measures": {}} for row in rows]
        groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            values = tuple(row.get(str(item["column"])) for item in dimensions)
            groups[values].append(row)
        output = []
        for values, group in groups.items():
            dimension_values = {
                str(item.get("alias") or str(item["column"]).split(".")[-1]): value
                for item, value in zip(dimensions, values, strict=True)
            }
            measure_values: dict[str, Any] = {}
            for item in measures:
                function = str(item["function"])
                column = str(item.get("column", "*"))
                values_for_measure = [row.get(column) for row in group if row.get(column) is not None]
                if function == "count":
                    value = len(group)
                elif function == "count_distinct":
                    value = len({str(item) for item in values_for_measure})
                elif function == "sum":
                    value = sum(float(item) for item in values_for_measure)
                elif function == "avg":
                    value = sum(float(item) for item in values_for_measure) / len(values_for_measure) if values_for_measure else None
                elif function == "min":
                    value = min(values_for_measure, default=None)
                elif function == "max":
                    value = max(values_for_measure, default=None)
                else:
                    raise ValueError(f"Unsupported Gold measure: {function}")
                measure_values[str(item["alias"])] = value
            output.append({"dimensions": dimension_values, "measures": measure_values})
        return output

    @staticmethod
    def _hash(value: Any) -> str:
        return hashlib.sha256(dumps(value).encode()).hexdigest()
