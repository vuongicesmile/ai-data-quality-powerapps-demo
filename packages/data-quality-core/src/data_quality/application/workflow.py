"""Complete governed Generic Dataset Demo application workflow."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from threading import RLock
from typing import Any
from uuid import uuid4

from data_quality.domain.errors import ConflictError, ResourceNotFoundError
from data_quality.domain.models import (
    ActivityEvent,
    ApprovalEvent,
    AssetMapping,
    GoldRecipe,
    MappingColumn,
    WorkflowState,
    utc_now,
)
from data_quality.domain.ports import BronzeStore, StateRepository, WarehouseRepository

from .profiling import is_null, profile_rows, quality_summary
from .rules import execute_rules, generate_rules


class GenericDatasetWorkflow:
    def __init__(
        self,
        *,
        bronze: BronzeStore,
        states: StateRepository,
        warehouse: WarehouseRepository,
    ) -> None:
        self.bronze = bronze
        self.states = states
        self.warehouse = warehouse
        self.lock = RLock()

    def overview(self, dataset_key: str) -> dict[str, Any]:
        return self._state(dataset_key).overview()

    def list_assets(self, dataset_key: str) -> list[dict[str, Any]]:
        return [asset.model_dump() for asset in self._state(dataset_key).assets.values()]

    def sync_from_bronze(self, dataset_key: str) -> dict[str, Any]:
        with self.lock:
            manifest, assets = self.bronze.load_latest_batch(dataset_key)
            state = WorkflowState(
                dataset_key=dataset_key,
                provider=str(manifest.get("provider", "sharepoint")),
                status="INGESTED",
                selected_asset_key="orders"
                if any(a.asset_key == "orders" for a in assets)
                else assets[0].asset_key,
                bronze_manifest=manifest,
                ingestion={"status": "SUCCESS", "progress": 100, "batch_id": manifest["batch_id"]},
            )
            for asset in assets:
                content = self.bronze.read_asset(asset)
                rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
                if not rows:
                    raise ValueError(f"Bronze CSV asset is empty: {asset.file_name}")
                state.assets[asset.asset_key] = asset
                state.rows[asset.asset_key] = rows
            state.lifecycle["ingested"] = True
            state.activity.append(
                self._event("SYNC_BRONZE", "SUCCESS", f"Loaded {len(assets)} assets")
            )
            self._save(state)
            return {"dataset": state.overview(), "assets": self.list_assets(dataset_key)}

    def set_ingestion(self, dataset_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key)
            state.ingestion = {**state.ingestion, **payload, "updated_at": utc_now()}
            self._save(state)
            return state.ingestion

    def select_asset(self, dataset_key: str, asset_key: str) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key)
            if asset_key not in state.assets:
                raise ResourceNotFoundError(f"Unknown asset: {asset_key}")
            state.selected_asset_key = asset_key
            self._save(state)
            return state.overview()

    def discover(self, dataset_key: str) -> dict[str, Any]:
        with self.lock:
            state = self._require_ingested(dataset_key)
            for asset_key, rows in state.rows.items():
                schema, _ = profile_rows(rows)
                state.schemas[asset_key] = schema
            state.lifecycle["discovered"] = True
            state.status = "DISCOVERED"
            state.activity.append(
                self._event("DISCOVER", "SUCCESS", "Discovered all asset schemas")
            )
            self._save(state)
            return {"schemas": state.schemas}

    def profile(self, dataset_key: str) -> dict[str, Any]:
        with self.lock:
            state = self._require_ingested(dataset_key)
            if not state.lifecycle["discovered"]:
                self.discover(dataset_key)
                state = self._state(dataset_key)
            for asset_key, rows in state.rows.items():
                schema, profiles = profile_rows(rows)
                state.schemas[asset_key] = schema
                state.profiles[asset_key] = profiles
                state.quality[asset_key] = quality_summary(profiles)
                state.rules[asset_key] = generate_rules(asset_key, profiles)
                state.mappings[asset_key] = self._suggest_mapping(asset_key, schema)
            state.lifecycle["profiled"] = True
            state.status = "PROFILED"
            state.activity.append(self._event("PROFILE", "SUCCESS", "Profiled all Bronze assets"))
            self._save(state)
            return self.get_profiles(dataset_key)

    def get_schema(self, dataset_key: str, asset_key: str | None = None) -> dict[str, Any]:
        state = self._state(dataset_key)
        key = asset_key or self._selected(state)
        return {"asset_key": key, "schema": state.schemas.get(key, [])}

    def get_profiles(self, dataset_key: str, asset_key: str | None = None) -> dict[str, Any]:
        state = self._state(dataset_key)
        key = asset_key or self._selected(state)
        results = state.rule_results.get(key, [])
        return {
            "asset_key": key,
            "profiles": [item.model_dump() for item in state.profiles.get(key, [])],
            "quality": state.quality.get(key, {}),
            "rules": [item.model_dump() for item in state.rules.get(key, [])],
            "rule_results": [item.model_dump() for item in results],
        }

    def list_rules(self, dataset_key: str, asset_key: str | None = None) -> dict[str, Any]:
        state = self._state(dataset_key)
        key = asset_key or self._selected(state)
        return {"asset_key": key, "rules": [rule.model_dump() for rule in state.rules.get(key, [])]}

    def review_rule(
        self,
        dataset_key: str,
        rule_id: str,
        *,
        decision: str,
        actor: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key)
            normalized = decision.upper()
            if normalized not in {"APPROVED", "REJECTED"}:
                raise ValueError("Rule decision must be APPROVED or REJECTED")
            for rules in state.rules.values():
                for rule in rules:
                    if rule.rule_id == rule_id:
                        rule.status = normalized
                        rule.reviewed_by = actor
                        rule.reviewed_at = utc_now()
                        if parameters is not None:
                            rule.parameters = parameters
                        state.activity.append(
                            self._event("REVIEW_RULE", normalized, rule_id, actor)
                        )
                        self._save(state)
                        return rule.model_dump()
            raise ResourceNotFoundError(f"Rule not found: {rule_id}")

    def approve_all_rules(self, dataset_key: str, *, actor: str) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key)
            count = 0
            for rules in state.rules.values():
                for rule in rules:
                    rule.status = "APPROVED"
                    rule.reviewed_by = actor
                    rule.reviewed_at = utc_now()
                    count += 1
            state.activity.append(self._event("APPROVE_RULES", "APPROVED", f"{count} rules", actor))
            self._save(state)
            return {"approved": count}

    def run_rules(self, dataset_key: str) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key, hydrate_rows=True)
            for asset_key, rows in state.rows.items():
                state.rule_results[asset_key] = execute_rules(
                    asset_key, rows, state.rules.get(asset_key, [])
                )
            violations = sum(
                result.violation_count
                for results in state.rule_results.values()
                for result in results
            )
            state.activity.append(
                self._event("EXECUTE_RULES", "SUCCESS", f"{violations} violations")
            )
            self._save(state)
            return {
                "violation_count": violations,
                "results": {
                    key: [result.model_dump() for result in results]
                    for key, results in state.rule_results.items()
                },
            }

    def evidence(
        self, dataset_key: str, *, asset_key: str, rule_id: str | None = None
    ) -> dict[str, Any]:
        state = self._state(dataset_key)
        results = state.rule_results.get(asset_key, [])
        evidence = [
            item
            for result in results
            if rule_id is None or result.rule_id == rule_id
            for item in result.evidence
        ]
        return {
            "asset_key": asset_key,
            "rule_id": rule_id,
            "evidence": evidence,
            "count": len(evidence),
        }

    def get_mapping(self, dataset_key: str, asset_key: str | None = None) -> dict[str, Any]:
        state = self._state(dataset_key)
        key = asset_key or self._selected(state)
        mapping = state.mappings.get(key)
        if not mapping:
            raise ConflictError("Profile the dataset before reviewing mappings")
        return mapping.model_dump()

    def approve_mapping(
        self, dataset_key: str, asset_key: str, *, actor: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key)
            current = state.mappings.get(asset_key)
            if not current:
                raise ResourceNotFoundError(f"Mapping not found: {asset_key}")
            mapping = AssetMapping.model_validate({**current.model_dump(), **(payload or {})})
            mapping.status = "APPROVED"
            mapping.approved_by = actor
            mapping.approved_at = utc_now()
            state.mappings[asset_key] = mapping
            state.activity.append(self._event("APPROVE_MAPPING", "APPROVED", asset_key, actor))
            self._save(state)
            return mapping.model_dump()

    def approve_all_mappings(self, dataset_key: str, *, actor: str) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key)
            for mapping in state.mappings.values():
                mapping.status = "APPROVED"
                mapping.approved_by = actor
                mapping.approved_at = utc_now()
            state.activity.append(self._event("APPROVE_MAPPINGS", "APPROVED", "all", actor))
            self._save(state)
            return {"approved": len(state.mappings)}

    def approve_layer(
        self,
        dataset_key: str,
        layer: str,
        *,
        decision: str,
        actor: str,
        reason: str = "",
    ) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key)
            normalized_layer = layer.upper()
            normalized_decision = decision.upper()
            if normalized_layer not in {"BRONZE", "SILVER", "GOLD"}:
                raise ValueError("Layer must be BRONZE, SILVER, or GOLD")
            if normalized_decision not in {"APPROVED", "REJECTED"}:
                raise ValueError("Decision must be APPROVED or REJECTED")
            if normalized_layer == "BRONZE" and not state.lifecycle["profiled"]:
                raise ConflictError("Profile the Bronze batch before approval")
            if normalized_layer == "SILVER" and not state.lifecycle["transformed"]:
                raise ConflictError("Publish Silver before approval")
            if normalized_layer == "GOLD" and not state.lifecycle["gold_published"]:
                raise ConflictError("Publish Gold before approval")
            event = ApprovalEvent(
                approval_id=f"approval_{uuid4().hex[:16]}",
                layer=normalized_layer,
                decision=normalized_decision,
                actor=actor,
                reason=reason,
            )
            state.approvals[normalized_layer] = event
            lifecycle_key = f"{normalized_layer.lower()}_approved"
            state.lifecycle[lifecycle_key] = normalized_decision == "APPROVED"
            state.activity.append(
                self._event(f"APPROVE_{normalized_layer}", normalized_decision, reason, actor)
            )
            self._save(state)
            return event.model_dump()

    def transform(self, dataset_key: str) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key, hydrate_rows=True)
            if not state.lifecycle["bronze_approved"]:
                raise ConflictError("Bronze must be approved before Silver transformation")
            if any(mapping.status != "APPROVED" for mapping in state.mappings.values()):
                raise ConflictError("All mappings must be approved before Silver transformation")
            batch_id = str(state.bronze_manifest["batch_id"])
            outputs = {}
            for asset_key, rows in state.rows.items():
                mapping = state.mappings[asset_key]
                valid, rejected = self._transform_rows(rows, mapping)
                publication = self.warehouse.publish_silver(
                    dataset_id=state.dataset_key,
                    asset_key=asset_key,
                    mapping=mapping.model_dump(),
                    rows=valid,
                    rejected_rows=rejected,
                    batch_id=batch_id,
                )
                outputs[asset_key] = {
                    **publication,
                    "input_rows": len(rows),
                    "valid_rows": len(valid),
                    "rejected_rows": len(rejected),
                    "rejections": rejected[:100],
                }
            state.silver = outputs
            state.lifecycle["transformed"] = True
            state.status = "SILVER_PUBLISHED"
            state.activity.append(
                self._event("PUBLISH_SILVER", "SUCCESS", f"{len(outputs)} assets")
            )
            self._save(state)
            return {"silver": outputs}

    def propose_gold_recipe(self, dataset_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key)
            recipe_id = str(payload.get("recipe_id") or f"recipe_{uuid4().hex[:12]}")
            previous = state.gold_recipes.get(recipe_id)
            recipe = GoldRecipe.model_validate(
                {
                    **payload,
                    "recipe_id": recipe_id,
                    "version": (previous.version + 1) if previous else 1,
                }
            )
            state.gold_recipes[recipe_id] = recipe
            state.activity.append(self._event("PROPOSE_GOLD", "DRAFT", recipe_id, recipe.actor))
            self._save(state)
            return recipe.model_dump()

    def review_gold_recipe(
        self, dataset_key: str, recipe_id: str, *, decision: str, actor: str
    ) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key)
            recipe = state.gold_recipes.get(recipe_id)
            if not recipe:
                raise ResourceNotFoundError(f"Gold recipe not found: {recipe_id}")
            normalized = decision.upper()
            if normalized not in {"APPROVED", "REJECTED"}:
                raise ValueError("Gold decision must be APPROVED or REJECTED")
            recipe.status = normalized
            recipe.reviewed_by = actor
            recipe.reviewed_at = utc_now()
            state.activity.append(self._event("REVIEW_GOLD", normalized, recipe_id, actor))
            self._save(state)
            return recipe.model_dump()

    def run_gold(self, dataset_key: str, recipe_id: str) -> dict[str, Any]:
        with self.lock:
            state = self._state(dataset_key)
            if not state.lifecycle["silver_approved"]:
                raise ConflictError("Silver must be approved before Gold publication")
            recipe = state.gold_recipes.get(recipe_id)
            if not recipe or recipe.status != "APPROVED":
                raise ConflictError("An approved Gold recipe is required")
            result = self.warehouse.publish_gold(
                dataset_id=state.dataset_key,
                recipe=recipe.model_dump(),
                silver=state.silver,
                batch_id=str(state.bronze_manifest["batch_id"]),
            )
            state.gold = {**result, "recipe_id": recipe_id, "recipe_version": recipe.version}
            state.lifecycle["gold_published"] = True
            state.status = "GOLD_PUBLISHED"
            state.activity.append(self._event("PUBLISH_GOLD", "SUCCESS", recipe_id))
            self._save(state)
            return state.gold

    def lineage(self, dataset_key: str) -> dict[str, Any]:
        state = self._state(dataset_key)
        return {
            "dataset_key": dataset_key,
            "nodes": [
                {
                    "id": "sharepoint",
                    "label": "SharePoint",
                    "status": "complete" if state.lifecycle["ingested"] else "pending",
                },
                {
                    "id": "bronze",
                    "label": "Bronze",
                    "status": "complete" if state.lifecycle["ingested"] else "pending",
                },
                {
                    "id": "profile",
                    "label": "Profile",
                    "status": "complete" if state.lifecycle["profiled"] else "pending",
                },
                {
                    "id": "silver",
                    "label": "Silver",
                    "status": "complete" if state.lifecycle["transformed"] else "pending",
                },
                {
                    "id": "gold",
                    "label": "Gold",
                    "status": "complete" if state.lifecycle["gold_published"] else "pending",
                },
            ],
            "edges": [
                {"from": "sharepoint", "to": "bronze"},
                {"from": "bronze", "to": "profile"},
                {"from": "profile", "to": "silver"},
                {"from": "silver", "to": "gold"},
            ],
            "activity": [event.model_dump() for event in state.activity[-100:]],
        }

    def list_gold_recipes(self, dataset_key: str) -> list[dict[str, Any]]:
        return [item.model_dump() for item in self._state(dataset_key).gold_recipes.values()]

    def get_silver(self, dataset_key: str) -> dict[str, Any]:
        return {"silver": self._state(dataset_key).silver}

    def get_gold(self, dataset_key: str) -> dict[str, Any]:
        return {"gold": self._state(dataset_key).gold}

    def _state(self, dataset_key: str, *, hydrate_rows: bool = False) -> WorkflowState:
        state = self.states.load(dataset_key) or WorkflowState(dataset_key=dataset_key)
        if hydrate_rows and state.assets and not state.rows:
            for asset_key, asset in state.assets.items():
                content = self.bronze.read_asset(asset)
                state.rows[asset_key] = list(
                    csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
                )
        return state

    def _require_ingested(self, dataset_key: str) -> WorkflowState:
        state = self._state(dataset_key, hydrate_rows=True)
        if not state.lifecycle["ingested"]:
            raise ConflictError("Sync a Bronze batch before running this operation")
        return state

    def _save(self, state: WorkflowState) -> None:
        state.revision += 1
        state.updated_at = utc_now()
        self.states.save(state)

    @staticmethod
    def _selected(state: WorkflowState) -> str:
        if not state.selected_asset_key:
            raise ConflictError("No dataset asset is selected")
        return state.selected_asset_key

    @staticmethod
    def _event(action: str, status: str, detail: str = "", actor: str = "system") -> ActivityEvent:
        return ActivityEvent(
            event_id=f"event_{uuid4().hex[:16]}",
            action=action,
            status=status,
            detail=detail,
            actor=actor,
        )

    @staticmethod
    def _suggest_mapping(asset_key: str, schema: list[dict[str, Any]]) -> AssetMapping:
        columns = [
            MappingColumn(
                source=item["column_name"],
                target=item["column_name"],
                type=item["physical_type"],
                nullable=bool(item["nullable"]),
            )
            for item in schema
        ]
        identifiers = [item.source for item in columns if item.source.endswith("_id")]
        return AssetMapping(
            asset_key=asset_key,
            columns=columns,
            business_key=identifiers[:1],
            target_table=f"dq_silverrow:{asset_key}",
        )

    @classmethod
    def _transform_rows(
        cls, rows: list[dict[str, Any]], mapping: AssetMapping
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        valid = []
        rejected = []
        for row_number, row in enumerate(rows, start=1):
            output: dict[str, Any] = {}
            errors = []
            for column in mapping.columns:
                value = row.get(column.source)
                if is_null(value):
                    if not column.nullable:
                        errors.append({"column": column.source, "code": "REQUIRED"})
                    output[column.target] = None
                    continue
                try:
                    output[column.target] = cls._convert(str(value), column.type)
                except (ValueError, InvalidOperation):
                    errors.append(
                        {"column": column.source, "code": f"INVALID_{column.type.upper()}"}
                    )
            if errors:
                rejected.append({"row_number": row_number, "errors": errors})
            else:
                output["_source_row_number"] = row_number
                valid.append(output)
        return valid, rejected

    @staticmethod
    def _convert(value: str, target: str) -> Any:
        if target == "Integer":
            return int(value)
        if target == "Decimal":
            return str(Decimal(value))
        if target == "Boolean":
            lowered = value.casefold()
            if lowered not in {"true", "false", "1", "0", "yes", "no"}:
                raise ValueError("invalid boolean")
            return lowered in {"true", "1", "yes"}
        if target == "Date":
            return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
        if target == "DateTime":
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        return value.strip()
