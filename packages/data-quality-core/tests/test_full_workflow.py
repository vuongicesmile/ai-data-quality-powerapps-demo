from pathlib import Path

from data_quality.application import GenericDatasetWorkflow, IngestionService
from data_quality.integrations.local_source import LocalDatasetSource
from data_quality.repositories import (
    InMemoryBronzeStore,
    InMemoryStateRepository,
    InMemoryWarehouseRepository,
)


def test_complete_bronze_to_gold_workflow() -> None:
    sample_root = Path(__file__).parents[3] / "sample-data" / "ecommerce-v1"
    source = LocalDatasetSource(sample_root)
    bronze = InMemoryBronzeStore()
    states = InMemoryStateRepository()
    warehouse = InMemoryWarehouseRepository()
    workflow = GenericDatasetWorkflow(bronze=bronze, states=states, warehouse=warehouse)

    manifest = IngestionService(source, bronze).run("ecommerce-v1")
    assert len(manifest["assets"]) == 4
    assert {item["file_name"] for item in manifest["assets"]} == {
        "customers.csv",
        "orders.csv",
        "order_items.csv",
        "products.csv",
    }

    workflow.sync_from_bronze("ecommerce-v1")
    workflow.discover("ecommerce-v1")
    profiles = workflow.profile("ecommerce-v1")
    assert profiles["asset_key"] == "orders"
    assert profiles["profiles"]

    assert workflow.approve_all_rules("ecommerce-v1", actor="tester")["approved"] > 0
    rule_run = workflow.run_rules("ecommerce-v1")
    assert rule_run["violation_count"] >= 0
    assert workflow.approve_all_mappings("ecommerce-v1", actor="tester")["approved"] == 4

    workflow.approve_layer(
        "ecommerce-v1", "BRONZE", decision="APPROVED", actor="tester"
    )
    silver = workflow.transform("ecommerce-v1")["silver"]
    assert set(silver) == {"customers", "orders", "order_items", "products"}
    workflow.approve_layer(
        "ecommerce-v1", "SILVER", decision="APPROVED", actor="tester"
    )

    recipe = workflow.propose_gold_recipe(
        "ecommerce-v1",
        {
            "target_asset": "orders_snapshot",
            "source_asset": "orders",
            "actor": "tester",
        },
    )
    workflow.review_gold_recipe(
        "ecommerce-v1", recipe["recipe_id"], decision="APPROVED", actor="tester"
    )
    gold = workflow.run_gold("ecommerce-v1", recipe["recipe_id"])
    assert gold["row_count"] == 5
    workflow.approve_layer(
        "ecommerce-v1", "GOLD", decision="APPROVED", actor="tester"
    )

    overview = workflow.overview("ecommerce-v1")
    assert overview["lifecycle"]["progress"] == 100
    assert overview["status"] == "GOLD_PUBLISHED"


def test_evidence_masks_email_values() -> None:
    sample_root = Path(__file__).parents[3] / "sample-data" / "ecommerce-v1"
    source = LocalDatasetSource(sample_root)
    bronze = InMemoryBronzeStore()
    workflow = GenericDatasetWorkflow(
        bronze=bronze,
        states=InMemoryStateRepository(),
        warehouse=InMemoryWarehouseRepository(),
    )
    IngestionService(source, bronze).run("ecommerce-v1")
    workflow.sync_from_bronze("ecommerce-v1")
    workflow.profile("ecommerce-v1")
    workflow.approve_all_rules("ecommerce-v1", actor="tester")
    workflow.run_rules("ecommerce-v1")
    evidence = workflow.evidence("ecommerce-v1", asset_key="customers")
    for item in evidence["evidence"]:
        assert "example.com" not in str(item.get("masked_value", "")) or "***@" in str(
            item["masked_value"]
        )
