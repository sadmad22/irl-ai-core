import json
from pathlib import Path


def test_production_orchestrator_schema_locks_canonical_stage_order_and_lifecycle():
    schema = json.loads(Path("shared/schemas/production-orchestration.schema.json").read_text(encoding="utf-8"))
    stage_enum = schema["$defs"]["stage"]["enum"]
    assert stage_enum == [
        "research", "intelligence", "configuration", "structure", "draft",
        "editorial_cleanup", "media", "linking", "optimization", "qa",
        "production_assembly", "article_package", "production_delivery_boundary", "wordpress_delivery",
    ]
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["properties"]["lifecycle_stage"]["enum"] == ["running", "failed", "completed", "human_review"]
    assert schema["properties"]["current_stage"]["oneOf"][0]["type"] == "null"
    assert schema["properties"]["production"]["$ref"] == "#/$defs/production"
