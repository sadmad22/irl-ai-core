import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agents.research.outline_editor import build_outline_editor_contract


def upstreams():
    strategy = {"strategy_id":"strat-1","report_id":"report-1","decision_id":"decision-1","schema_version":"1.0","lifecycle_stage":"content_strategy_ready","content_type":"guide","primary_keyword":"consultant insurance","sections":["Introduction","What You Need to Know","How to Choose"],"evidence_refs":["ev-1"]}
    config = {"config_id":"config-1","brief_id":"brief-1","report_id":"report-1","decision_id":"decision-1","strategy_id":"strat-1","schema_version":"1.0","lifecycle_stage":"article_config_ready","article_type":"guide"}
    structure = {"structure_id":"structure-1","brief_id":"brief-1","report_id":"report-1","decision_id":"decision-1","strategy_id":"strat-1","schema_version":"1.0","lifecycle_stage":"article_structure_ready","hook":{"required":True,"hook_type":"direct_answer"},"conclusion":{"required":True},"h3":{"min":0,"max":2},"tables":{"enabled":True,"required":False,"count":{"min":0,"max":1}},"lists":{"enabled":True,"required":False,"count":{"min":0,"max":2}},"faq":{"enabled":True,"required":False,"count":{"min":0,"max":5},"answer_required":True}}
    details = {"details_to_include_id":"details-1","brief_id":"brief-1","report_id":"report-1","decision_id":"decision-1","strategy_id":"strat-1","config_id":"config-1","schema_version":"1.0","lifecycle_stage":"details_to_include_ready","details_to_include":{"key_takeaways":{"enabled":True,"required":True,"count":{"min":3,"target":4,"max":5}},"quotes":{"enabled":True,"required":False,"count":{"min":0,"target":1,"max":2},"source_requirement":"verified_source_evidence","attribution_required":True,"evidence_gate":"verified_evidence_required"},"bold":{"enabled":True,"required":False,"max_per_section":3,"policy":"editorial_emphasis_only"}},"audit":{"method":"deterministic-details-to-include","method_version":"v1","validation_status":"validated"}}
    return strategy, config, structure, details


def test_default_outline_is_deterministic_and_preserves_strategy_order():
    args = list(upstreams())
    first = build_outline_editor_contract(content_strategy=args[0], article_configuration=args[1], article_structure=args[2], details_to_include=args[3])
    second = build_outline_editor_contract(content_strategy=args[0], article_configuration=args[1], article_structure=args[2], details_to_include=args[3])
    assert first == second
    assert [s["heading"] for s in first["sections"]] == args[0]["sections"]
    assert first["lifecycle_stage"] == "outline_editor_ready"


def test_custom_outline_is_normalized_and_keeps_editability():
    args = list(upstreams())
    custom = [{"order":1,"heading":"Introduction","level":"H2","required":True,"purpose":"Set context"},{"order":2,"heading":"Coverage","level":"H3","required":True,"notes":"Explain major exposures"}]
    result = build_outline_editor_contract(content_strategy=args[0], article_configuration=args[1], article_structure=args[2], details_to_include=args[3], outline=custom)
    assert result["sections"][1]["level"] == "H3"
    assert result["sections"][1]["notes"] == "Explain major exposures"


def test_rejects_lineage_mismatch():
    args = list(upstreams())
    args[1] = dict(args[1], strategy_id="other")
    with pytest.raises(ValueError, match="Lineage mismatch"):
        build_outline_editor_contract(content_strategy=args[0], article_configuration=args[1], article_structure=args[2], details_to_include=args[3])


def test_rejects_h3_out_of_structure_bounds():
    args = list(upstreams())
    args[2] = dict(args[2], h3={"min":2,"max":2})
    with pytest.raises(ValueError, match="H3 count"):
        build_outline_editor_contract(content_strategy=args[0], article_configuration=args[1], article_structure=args[2], details_to_include=args[3])


def test_rejects_duplicate_or_noncontiguous_order():
    args = list(upstreams())
    with pytest.raises(ValueError, match="unique"):
        build_outline_editor_contract(content_strategy=args[0], article_configuration=args[1], article_structure=args[2], details_to_include=args[3], outline=[{"order":1,"heading":"A","level":"H2","required":True},{"order":1,"heading":"B","level":"H2","required":True}])


def test_rejects_unknown_heading_level():
    args = list(upstreams())
    with pytest.raises(ValueError, match="H2 or H3"):
        build_outline_editor_contract(content_strategy=args[0], article_configuration=args[1], article_structure=args[2], details_to_include=args[3], outline=[{"order":1,"heading":"A","level":"H4","required":True}])


def test_does_not_mutate_inputs():
    args = list(upstreams())
    before = copy.deepcopy(args)
    build_outline_editor_contract(content_strategy=args[0], article_configuration=args[1], article_structure=args[2], details_to_include=args[3])
    assert args == before


def test_output_validates_against_schema():
    args = list(upstreams())
    output = build_outline_editor_contract(content_strategy=args[0], article_configuration=args[1], article_structure=args[2], details_to_include=args[3])
    schema = json.loads(Path("shared/schemas/outline-editor.schema.json").read_text())
    Draft202012Validator(schema).validate(output)


def test_no_writer_or_provider_fields():
    args = list(upstreams())
    output = build_outline_editor_contract(content_strategy=args[0], article_configuration=args[1], article_structure=args[2], details_to_include=args[3])
    forbidden = {"prompt","llm","provider","model","prose","body","generated_text"}
    assert forbidden.isdisjoint(output)
