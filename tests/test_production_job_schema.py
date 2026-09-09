import json
from pathlib import Path


def test_production_job_schema_locks_status_enum_and_core_fields():
    schema = json.loads(Path("shared/schemas/production-job.schema.json").read_text(encoding="utf-8"))
    props = schema["properties"]

    assert props["schema_version"]["const"] == "1.0"
    assert props["status"]["enum"] == [
        "queued", "researching", "building", "drafting", "editing",
        "optimizing", "qa", "ready", "published", "failed",
    ]
    assert props["current_stage"]["enum"] == [
        "research", "intelligence", "configuration", "structure", "draft",
        "editorial_cleanup", "media", "linking", "optimization", "qa",
        "article_package", None,
    ]
    assert props["job_id"]["pattern"] == r"^job_[a-f0-9]{16}$"
    assert props["ready_to_publish"]["type"] == "boolean"


def test_production_job_schema_locks_lineage_and_error_shape():
    schema = json.loads(Path("shared/schemas/production-job.schema.json").read_text(encoding="utf-8"))
    lineage = schema["properties"]["lineage"]
    error = schema["properties"]["error"]

    assert lineage["required"] == ["project_name"]
    assert set(lineage["properties"]) == {"project_name", "orchestration_id", "production_id"}
    assert error["type"] == ["object", "null"]
    assert error["required"] == ["stage", "type", "message"]
