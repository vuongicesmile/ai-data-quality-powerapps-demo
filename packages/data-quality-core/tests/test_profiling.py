from data_quality.application.profiling import infer_physical_type, profile_rows


def test_infers_deterministic_types_and_counts() -> None:
    rows = [
        {"id": "1", "amount": "10.50", "email": "a@example.com"},
        {"id": "2", "amount": "", "email": ""},
        {"id": "2", "amount": "20.25", "email": "b@example.com"},
    ]
    schema, profiles = profile_rows(rows)
    assert [item["physical_type"] for item in schema] == ["Integer", "Decimal", "String"]
    by_name = {profile.column_name: profile for profile in profiles}
    assert by_name["id"].duplicate_count == 1
    assert by_name["amount"].null_count == 1
    assert by_name["email"].semantic_type == "EMAIL"


def test_empty_values_fall_back_to_string() -> None:
    assert infer_physical_type(["", None, "null"]) == "String"
