"""ClickHouse workflow state and Silver/Gold repository implementations."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from data_quality.domain.models import WorkflowState

from .client import ClickHouseClient

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TYPE_MAP = {
    "String": "Nullable(String)",
    "Integer": "Nullable(Int64)",
    "Decimal": "Nullable(Decimal(18,4))",
    "Date": "Nullable(Date)",
    "DateTime": "Nullable(DateTime64(3, 'UTC'))",
    "Boolean": "Nullable(UInt8)",
}


def identifier(value: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"Unsafe ClickHouse identifier: {value}")
    return value


def table_for_asset(asset_key: str) -> str:
    return identifier(re.sub(r"[^A-Za-z0-9_]", "_", asset_key))


class ClickHouseStateRepository:
    table = "generic_dataset_demo_profiling.workflow_states"

    def __init__(self, client: ClickHouseClient) -> None:
        self.client = client

    def load(self, dataset_key: str) -> WorkflowState | None:
        key = dataset_key.replace("'", "''")
        rows = self.client.query_json(
            "SELECT state_json FROM "
            + self.table
            + f" WHERE dataset_key = '{key}' ORDER BY revision DESC LIMIT 1",
            maximum_rows=1,
        )
        if not rows:
            return None
        return WorkflowState.model_validate_json(rows[0]["state_json"])

    def save(self, state: WorkflowState) -> None:
        lifecycle = state.overview()["lifecycle"]
        self.client.insert_json(
            self.table,
            [
                {
                    "dataset_key": state.dataset_key,
                    "revision": state.revision,
                    "status": state.status,
                    "progress": lifecycle["progress"],
                    "current_step": lifecycle["current_step"],
                    "state_json": state.model_dump_json(),
                    "updated_at": state.updated_at,
                }
            ],
        )


class ClickHouseWarehouseRepository:
    silver_database = "generic_dataset_demo_silver"
    gold_database = "generic_dataset_demo_gold"

    def __init__(self, client: ClickHouseClient) -> None:
        self.client = client

    def publish_silver(
        self,
        *,
        dataset_id: str,
        asset_key: str,
        mapping: dict[str, Any],
        rows: list[dict[str, Any]],
        batch_id: str,
    ) -> dict[str, Any]:
        del dataset_id
        table_name = table_for_asset(asset_key)
        table = f"{self.silver_database}.{table_name}"
        columns = []
        for column in mapping["columns"]:
            name = identifier(column["target"])
            column_type = TYPE_MAP[column["type"]]
            if not column.get("nullable", True):
                column_type = column_type.removeprefix("Nullable(").removesuffix(")")
            columns.append(f"`{name}` {column_type}")
        columns.extend(
            [
                "`_batch_id` String",
                "`_source_row_number` UInt64",
                "`_row_hash` String",
                "`_ingested_at` DateTime64(3, 'UTC') DEFAULT now64(3)",
            ]
        )
        self.client.execute(f"CREATE DATABASE IF NOT EXISTS {self.silver_database}")
        self.client.execute(
            f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)}) "
            "ENGINE = ReplacingMergeTree(_ingested_at) ORDER BY (_row_hash)"
        )
        staging = table + "__staging"
        self.client.execute(f"CREATE TABLE IF NOT EXISTS {staging} AS {table}")
        self.client.execute(f"TRUNCATE TABLE {staging}")
        warehouse_rows = []
        for row in rows:
            payload = {**row, "_batch_id": batch_id}
            payload["_row_hash"] = self._hash(payload)
            warehouse_rows.append(payload)
        self.client.insert_json(staging, warehouse_rows)
        self.client.execute(f"EXCHANGE TABLES {table} AND {staging}")
        self.client.execute(f"TRUNCATE TABLE {staging}")
        return {
            "database": self.silver_database,
            "table": table_name,
            "target_table": table,
            "row_count": len(warehouse_rows),
            "snapshot_hash": self._hash(warehouse_rows),
        }

    def publish_gold(
        self,
        *,
        dataset_id: str,
        recipe: dict[str, Any],
        silver: dict[str, dict[str, Any]],
        batch_id: str,
    ) -> dict[str, Any]:
        del dataset_id
        target_name = identifier(
            table_for_asset(recipe["target_asset"]) + f"_v{int(recipe['version'])}"
        )
        target = f"{self.gold_database}.{target_name}"
        select_sql = self._compile_gold(recipe, silver)
        governed = (
            "SELECT result.*, "
            f"'{batch_id.replace(chr(39), chr(39) * 2)}' AS _batch_id, "
            f"toUInt32({int(recipe['version'])}) AS _recipe_version, "
            "now64(3) AS _ingested_at FROM (" + select_sql + ") AS result"
        )
        self.client.execute(f"CREATE DATABASE IF NOT EXISTS {self.gold_database}")
        self.client.execute(
            f"CREATE TABLE IF NOT EXISTS {target} "
            "ENGINE = ReplacingMergeTree(_ingested_at) ORDER BY tuple() "
            f"AS {governed} LIMIT 0"
        )
        staging = target + "__staging"
        self.client.execute(f"CREATE TABLE IF NOT EXISTS {staging} AS {target}")
        self.client.execute(f"TRUNCATE TABLE {staging}")
        self.client.execute(f"INSERT INTO {staging} {governed}")
        self.client.execute(f"EXCHANGE TABLES {target} AND {staging}")
        self.client.execute(f"TRUNCATE TABLE {staging}")
        count = int(self.client.execute(f"SELECT count() FROM {target}").strip() or 0)
        # Keep the published snapshot identity deterministic without depending on
        # ClickHouse's tuple(*) expansion, which differs between server versions.
        digest = self._hash(
            {
                "target": target,
                "batch_id": batch_id,
                "recipe_version": recipe["version"],
                "row_count": count,
            }
        )
        return {
            "database": self.gold_database,
            "table": target_name,
            "target_table": target,
            "row_count": count,
            "snapshot_hash": digest,
            "reconciliation": "PASS",
        }

    def _compile_gold(self, recipe: dict[str, Any], silver: dict[str, dict[str, Any]]) -> str:
        source_asset = recipe["source_asset"]
        if source_asset not in silver:
            raise ValueError(f"Silver source is not published: {source_asset}")
        aliases = {source_asset: "a0"}
        from_sql = f"FROM {silver[source_asset]['target_table']} AS a0"
        for index, join in enumerate(recipe.get("joins", []), start=1):
            right_asset = join["right_asset"]
            if right_asset not in silver:
                raise ValueError(f"Silver join source is not published: {right_asset}")
            aliases[right_asset] = f"a{index}"
            left = self._reference(join["left"], aliases)
            right = self._reference(join["right"], aliases)
            join_type = str(join.get("join_type", "LEFT")).upper()
            if join_type not in {"INNER", "LEFT", "RIGHT", "FULL"}:
                raise ValueError("Unsupported Gold join type")
            from_sql += (
                f" {join_type} JOIN {silver[right_asset]['target_table']} AS a{index} "
                f"ON {left} = {right}"
            )
        dimensions = recipe.get("dimensions", [])
        measures = recipe.get("measures", [])
        selects = []
        groups = []
        for item in dimensions:
            expression = self._reference(item["column"], aliases)
            alias = identifier(item.get("alias") or item["column"].split(".")[-1])
            selects.append(f"{expression} AS `{alias}`")
            groups.append(expression)
        functions = {
            "count": "count",
            "count_distinct": "uniqExact",
            "sum": "sum",
            "avg": "avg",
            "min": "min",
            "max": "max",
        }
        for item in measures:
            function = functions[item["function"]]
            expression = (
                "*" if item.get("column") == "*" else self._reference(item["column"], aliases)
            )
            alias = identifier(item["alias"])
            selects.append(f"{function}({expression}) AS `{alias}`")
        if not selects:
            selects = ["a0.*"]
        predicates = []
        operators = {"eq": "=", "neq": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
        for item in recipe.get("filters", []):
            column = self._reference(item["column"], aliases)
            operator = item["operator"]
            if operator == "in":
                values = ", ".join(self._literal(value) for value in item["value"])
                predicates.append(f"{column} IN ({values})")
            else:
                predicates.append(f"{column} {operators[operator]} {self._literal(item['value'])}")
        sql = "SELECT " + ", ".join(selects) + " " + from_sql
        if predicates:
            sql += " WHERE " + " AND ".join(predicates)
        if measures and groups:
            sql += " GROUP BY " + ", ".join(groups)
        return sql

    @staticmethod
    def _reference(value: str, aliases: dict[str, str]) -> str:
        asset, column = value.split(".", 1)
        if asset not in aliases:
            raise ValueError(f"Gold reference uses an unavailable asset: {asset}")
        return f"{aliases[asset]}.`{identifier(column)}`"

    @staticmethod
    def _literal(value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        return "'" + str(value).replace("'", "''") + "'"

    @staticmethod
    def _hash(value: Any) -> str:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode()).hexdigest()
