#!/usr/bin/env python3
"""Run the complete governed demo lifecycle against a running API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
DATASET = os.getenv("DATASET_KEY", "ecommerce-v1")
ACTOR = os.getenv("DEMO_ACTOR", "smoke-test")


def request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    payload = None if body is None else json.dumps(body).encode()
    call = urllib.request.Request(
        BASE_URL + path,
        data=payload,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(call, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} failed ({exc.code}): {detail}") from exc


def post(path: str, body: dict[str, Any] | None = None) -> Any:
    return request("POST", path, body or {})


def main() -> None:
    root = f"/api/v1/datasets/{DATASET}"
    steps: list[tuple[str, Any]] = []

    steps.append(("ingest", post(f"{root}/ingestion-runs", {"force": True})))
    steps.append(("discover", post(f"{root}/discover")))
    steps.append(("profile", post(f"{root}/profile")))
    steps.append(("approve rules", post(f"{root}/rules/approve-all", {"actor": ACTOR})))
    steps.append(("execute rules", post(f"{root}/rules/execute")))
    steps.append(("approve mappings", post(f"{root}/mappings/approve-all", {"actor": ACTOR})))
    approval = {"decision": "APPROVED", "actor": ACTOR, "reason": "smoke test"}
    steps.append(("approve Bronze", post(f"{root}/approvals/BRONZE", approval)))
    steps.append(("publish Silver", post(f"{root}/silver/run")))
    steps.append(("approve Silver", post(f"{root}/approvals/SILVER", approval)))

    recipe = post(
        f"{root}/gold/recipes",
        {
            "recipe_id": "orders_by_status",
            "target_asset": "orders_by_status",
            "source_asset": "orders",
            "dimensions": [{"column": "orders.status", "alias": "status"}],
            "measures": [{"function": "count", "column": "*", "alias": "order_count"}],
            "actor": ACTOR,
        },
    )
    steps.append(("create Gold recipe", recipe))
    steps.append(
        (
            "approve Gold recipe",
            post(
                f"{root}/gold/recipes/{recipe['recipe_id']}/review",
                {"decision": "APPROVED", "actor": ACTOR},
            ),
        )
    )
    steps.append(
        (
            "publish Gold",
            post(f"{root}/gold/run", {"recipe_id": recipe["recipe_id"]}),
        )
    )
    steps.append(("approve Gold", post(f"{root}/approvals/GOLD", approval)))

    dataset = request("GET", root)
    assert dataset["lifecycle"]["progress"] == 100, dataset["lifecycle"]
    assert dataset["lifecycle"]["current_step"] == "completed"
    assert len(request("GET", f"{root}/lineage")["nodes"]) == 5
    print(f"PASS: {len(steps)} lifecycle actions; progress=100%; revision={dataset['revision']}")


if __name__ == "__main__":
    main()
