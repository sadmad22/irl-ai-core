import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from agents.research.external_linking import build_external_linking_contract


def outline():
    return {
        "outline_editor_id": "outline-1", "brief_id": "brief-1", "report_id": "report-1",
        "decision_id": "decision-1", "strategy_id": "strat-1", "config_id": "config-1",
        "structure_id": "structure-1", "details_to_include_id": "details-1",
        "schema_version": "1.0", "lifecycle_stage": "outline_editor_ready",
        "sections": [{"order": 1, "heading": "Introduction", "level": "H2", "required": True}],
    }


def candidate(url="https://example.org/research/insurance", score=0.8, source="search", link_type="research"):
    return {
        "url": url, "title": "Insurance research", "domain": "example.org",
        "relevance_score": score, "source": source, "link_type": link_type,
    }


def schema():
    return json.loads(Path("shared/schemas/external-linking.schema.json").read_text())


def test_default_is_enabled_not_required_and_deterministic():
    candidates = [candidate()]
    first = build_external_linking_contract(outline_editor=outline(), candidates=candidates)
    second = build_external_linking_contract(outline_editor=outline(), candidates=candidates)
    assert first == second
    assert first["external_linking"]["max_links"] == 3
    assert first["external_linking"]["links"][0]["url"] == candidates[0]["url"]


def test_selects_highest_relevance_deterministically():
    result = build_external_linking_contract(
        outline_editor=outline(),
        candidates=[candidate("https://example.org/low", .2), candidate("https://example.org/high", .9), candidate("https://example.org/mid", .5)],
        max_links=2,
    )
    assert [item["url"] for item in result["external_linking"]["links"]] == ["https://example.org/high", "https://example.org/mid"]


def test_equal_scores_use_url_tiebreaker():
    result = build_external_linking_contract(
        outline_editor=outline(),
        candidates=[candidate("https://example.org/z", .5), candidate("https://example.org/a", .5)],
        max_links=2,
    )
    assert [item["url"] for item in result["external_linking"]["links"]] == ["https://example.org/a", "https://example.org/z"]


def test_required_requires_enabled_and_verified_candidate():
    with pytest.raises(ValueError, match="required cannot be true"):
        build_external_linking_contract(outline_editor=outline(), required=True, enabled=False, max_links=0)
    with pytest.raises(ValueError, match="at least one verified candidate"):
        build_external_linking_contract(outline_editor=outline(), required=True, enabled=True, max_links=1, candidates=[])


def test_disabled_requires_zero_max_and_emits_no_links():
    result = build_external_linking_contract(outline_editor=outline(), enabled=False, max_links=0, candidates=[candidate()])
    assert result["external_linking"]["links"] == []
    with pytest.raises(ValueError, match="max_links must be zero"):
        build_external_linking_contract(outline_editor=outline(), enabled=False, max_links=1)


def test_rejects_duplicate_urls():
    with pytest.raises(ValueError, match="must be unique"):
        build_external_linking_contract(outline_editor=outline(), candidates=[candidate(), candidate()])


def test_rejects_invalid_source_and_mismatch_with_requirement():
    bad = candidate(source="other")
    with pytest.raises(ValueError, match="source must be dataforseo or search"):
        build_external_linking_contract(outline_editor=outline(), candidates=[bad])
    mismatch = candidate(source="dataforseo")
    with pytest.raises(ValueError, match="must match source_requirement"):
        build_external_linking_contract(outline_editor=outline(), candidates=[mismatch], source_requirement="search")


def test_rejects_non_https_url_and_invalid_link_type():
    bad_url = candidate(url="http://example.org/research")
    with pytest.raises(ValueError, match="must use HTTPS"):
        build_external_linking_contract(outline_editor=outline(), candidates=[bad_url])
    bad_type = candidate(link_type="video")
    with pytest.raises(ValueError, match="link_type must be one of"):
        build_external_linking_contract(outline_editor=outline(), candidates=[bad_type])


def test_rejects_unknown_candidate_fields():
    item = candidate(); item["anchor_text"] = "insurance"
    with pytest.raises(ValueError, match="unsupported fields"):
        build_external_linking_contract(outline_editor=outline(), candidates=[item])


def test_rejects_wrong_outline_lifecycle():
    source = outline(); source["lifecycle_stage"] = "youtube_videos_ready"
    with pytest.raises(ValueError, match="outline_editor_ready"):
        build_external_linking_contract(outline_editor=source)


def test_does_not_mutate_inputs():
    source = outline(); candidates = [candidate()]
    before_source = copy.deepcopy(source); before_candidates = copy.deepcopy(candidates)
    build_external_linking_contract(outline_editor=source, candidates=candidates)
    assert source == before_source
    assert candidates == before_candidates


def test_output_validates_against_schema():
    output = build_external_linking_contract(outline_editor=outline(), candidates=[candidate()])
    Draft202012Validator(schema()).validate(output)


@pytest.mark.parametrize("settings", [
    {"enabled": False, "required": False, "max_links": 1, "links": [candidate()]},
    {"enabled": False, "required": True, "max_links": 0, "links": []},
    {"enabled": True, "required": False, "max_links": 0, "links": []},
])
def test_schema_rejects_cross_field_invariant_violations(settings):
    output = build_external_linking_contract(outline_editor=outline(), candidates=[candidate()])
    output["external_linking"].update(settings)
    with pytest.raises(ValidationError):
        Draft202012Validator(schema()).validate(output)


def test_schema_rejects_unknown_nested_field():
    output = build_external_linking_contract(outline_editor=outline())
    output["external_linking"]["unexpected"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema()).validate(output)


def test_no_llm_or_internal_linking_fields():
    output = build_external_linking_contract(outline_editor=outline())
    forbidden = {"prompt", "llm", "provider", "model", "anchor_text", "internal_url", "wordpress", "html", "generated_text"}
    assert forbidden.isdisjoint(output)
