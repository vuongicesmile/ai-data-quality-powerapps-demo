CREATE DATABASE IF NOT EXISTS generic_dataset_demo_profiling;
CREATE DATABASE IF NOT EXISTS generic_dataset_demo_silver;
CREATE DATABASE IF NOT EXISTS generic_dataset_demo_gold;

CREATE TABLE IF NOT EXISTS generic_dataset_demo_profiling.workflow_states
(
    dataset_key String,
    revision UInt64,
    status LowCardinality(String),
    progress UInt8,
    current_step String,
    state_json String,
    updated_at DateTime64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(revision)
ORDER BY (dataset_key, revision);

CREATE TABLE IF NOT EXISTS generic_dataset_demo_profiling.audit_events
(
    dataset_key String,
    event_id String,
    action LowCardinality(String),
    status LowCardinality(String),
    actor String,
    detail String,
    recorded_at DateTime64(3, 'UTC')
)
ENGINE = MergeTree
ORDER BY (dataset_key, recorded_at, event_id);

CREATE TABLE IF NOT EXISTS generic_dataset_demo_profiling.profile_results
(
    dataset_key String,
    asset_key String,
    batch_id String,
    profile_json String,
    quality_json String,
    persisted_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(persisted_at)
ORDER BY (dataset_key, asset_key, batch_id);

CREATE TABLE IF NOT EXISTS generic_dataset_demo_profiling.approval_events
(
    dataset_key String,
    approval_id String,
    layer LowCardinality(String),
    decision LowCardinality(String),
    actor String,
    reason String,
    recorded_at DateTime64(3, 'UTC')
)
ENGINE = MergeTree
ORDER BY (dataset_key, layer, recorded_at);
