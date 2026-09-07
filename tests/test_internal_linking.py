import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from agents.research.internal_linking import build_internal_linking_contract


SITE = "insurancereviewlab.com"


def outline():
    return {
        "outline_editor_id": "outline-1", "brief_id": "brief-1", "report_id": "report-1",
        "decision_id": "decision-1", "strategy_id": "strat-1", "config_id": "config-1",
        "structure_id": "structure-1", "details_to_include_id": "details-1",
        "schema_version": "1.0", "lifecycle_stage": "outline_editor_ready",
        "sections": [{"order": 1, "heading": "Introduction", "level": "H2", "required": True}],
    }


def candidate(url="https://insurancereviewlab.com/guides/insurance", score=0.8, source="local_index", link_type="guide", post_id="post-1"):
    return {
        "post_id": post_id, "url": url, "title": "Insurance guide", "slug": "guides/insurance",
        "relevance_score": score, "source": source, "link_type": link_type,
    }


def schema():
    return json.loads(Path("shared/schemas/internal-linking.schema.json").read_text())


def test_default_is_enabled_not_required_and_deterministic():
    candidates = [candidate()]
    first = build_internal_linking_contract(outline_editor=outline(), candidates=candidates, site_domain=SITE)
    second = build_internal_linking_contract(outline_editor=outline(), candidates=candidates, site_domain=SITE)
    assert first == second
    assert first["internal_linking"]["max_links"] == 3
    assert first["internal_linking"]["links"][0]["url"] == candidates[0]["url"]
    assert first["internal_linking"]["site_domain"] == SITE
    assert first["internal_linking"]["current_url"] is None


def test_selects_highest_relevance_deterministically():
    result = build_internal_linking_contract(
        outline_editor=outline(),
        candidates=[
            candidate("https://insurancereviewlab.com/low", .2, post_id="p-low"),
            candidate("https://insurancereviewlab.com/high", .9, post_id="p-high"),
            candidate("https://insurancereviewlab.com/mid", .5, post_id="p-mid"),
        ],
        site_domain=SITE,
        max_links=2,
    )
    assert [item["url"] for item in result["internal_linking"]["links"]] == [
        "https://insurancereviewlab.com/high", "https://insurancereviewlab.com/mid"
    ]


def test_equal_scores_use_url_tiebreaker():
    result = build_internal_linking_contract(
        outline_editor=outline(),
        candidates=[
            candidate("https://insurancereviewlab.com/z", .5, post_id="p-z"),
            candidate("https://insurancereviewlab.com/a", .5, post_id="p-a"),
        ],
        site_domain=SITE,
        max_links=2,
    )
    assert [item["url"] for item in result["internal_linking"]["links"]] == [
        "https://insurancereviewlab.com/a", "https://insurancereviewlab.com/z"
    ]


def test_required_requires_enabled_and_verified_candidate():
    with pytest.raises(ValueError, match="required cannot be true"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, required=True, enabled=False, max_links=0)
    with pytest.raises(ValueError, match="at least one verified candidate"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, required=True, enabled=True, max_links=1, candidates=[])


def test_disabled_requires_zero_max_and_emits_no_links():
    result = build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, enabled=False, max_links=0, candidates=[candidate()])
    assert result["internal_linking"]["links"] == []
    with pytest.raises(ValueError, match="max_links must be zero"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, enabled=False, max_links=1)


def test_rejects_duplicate_post_ids_and_urls():
    with pytest.raises(ValueError, match="post_ids must be unique"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[candidate("https://insurancereviewlab.com/a"), candidate("https://insurancereviewlab.com/b")])
    with pytest.raises(ValueError, match="URLs must be unique"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[candidate(), candidate(post_id="post-2")])


def test_rejects_external_domain_and_self_link():
    with pytest.raises(ValueError, match="belong to site_domain"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[candidate("https://example.org/a")])
    with pytest.raises(ValueError, match="current article"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, current_url="https://insurancereviewlab.com/current", candidates=[candidate("https://insurancereviewlab.com/current")])


def test_rejects_invalid_source_and_mismatch_with_requirement():
    bad = candidate(source="other")
    with pytest.raises(ValueError, match="source must be wordpress_api or local_index"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[bad])
    mismatch = candidate(source="wordpress_api")
    with pytest.raises(ValueError, match="must match source_requirement"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[mismatch], source_requirement="local_index")


def test_rejects_non_https_url_and_invalid_link_type():
    with pytest.raises(ValueError, match="must be an HTTPS URL"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[candidate("http://insurancereviewlab.com/a")])
    with pytest.raises(ValueError, match="link_type must be one of"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[candidate(link_type="video")])


def test_rejects_invalid_slug_and_unknown_candidate_fields():
    item = candidate(); item["anchor_text"] = "insurance"
    with pytest.raises(ValueError, match="unsupported fields"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[item])
    item = candidate(); item["slug"] = "/guides/insurance"
    with pytest.raises(ValueError, match="relative slug"):
        build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[item])


def test_rejects_wrong_outline_lifecycle():
    source = outline(); source["lifecycle_stage"] = "youtube_videos_ready"
    with pytest.raises(ValueError, match="outline_editor_ready"):
        build_internal_linking_contract(outline_editor=source, site_domain=SITE)


def test_does_not_mutate_inputs():
    source = outline(); candidates = [candidate()]
    before_source = copy.deepcopy(source); before_candidates = copy.deepcopy(candidates)
    build_internal_linking_contract(outline_editor=source, site_domain=SITE, candidates=candidates)
    assert source == before_source
    assert candidates == before_candidates


def test_output_validates_against_schema():
    output = build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[candidate()], current_url="https://insurancereviewlab.com/current")
    Draft202012Validator(schema()).validate(output)


@pytest.mark.parametrize("settings", [
    {"enabled": False, "required": False, "max_links": 1, "links": [candidate()]},
    {"enabled": False, "required": True, "max_links": 0, "links": []},
    {"enabled": True, "required": False, "max_links": 0, "links": []},
])
def test_schema_rejects_cross_field_invariant_violations(settings):
    output = build_internal_linking_contract(outline_editor=outline(), site_domain=SITE, candidates=[candidate()])
    output["internal_linking"].update(settings)
    with pytest.raises(ValidationError):
        Draft202012Validator(schema()).validate(output)


def test_schema_rejects_unknown_nested_field():
    output = build_internal_linking_contract(outline_editor=outline(), site_domain=SITE)
    output["internal_linking"]["unexpected"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema()).validate(output)


def test_no_llm_or_external_linking_fields():
    output = build_internal_linking_contract(outline_editor=outline(), site_domain=SITE)
    forbidden = {"prompt", "llm", "provider", "model", "anchor_text", "external_url", "html", "generated_text", "dataforseo", "search"}
    assert forbidden.isdisjoint(output)
