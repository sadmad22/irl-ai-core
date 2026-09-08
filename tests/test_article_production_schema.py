import json
from pathlib import Path


def test_article_production_schema_declares_locked_contract():
    path = Path("shared/schemas/article-production.schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))

    assert schema["$schema"].endswith("draft/2020-12/schema")
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["properties"]["lifecycle_stage"]["const"] == "production_ready"
    assert schema["properties"]["publication"]["properties"]["publish"]["const"] is False
    assert schema["properties"]["publication"]["properties"]["human_approval_required"]["const"] is True

    required_lineage = schema["properties"]["lineage"]["required"]
    assert required_lineage == [
        "report_id",
        "decision_id",
        "strategy_id",
        "brief_id",
        "draft_id",
        "quality_id",
    ]
