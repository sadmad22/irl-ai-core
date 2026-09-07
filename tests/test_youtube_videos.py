import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from agents.research.youtube_videos import build_youtube_videos_contract


def outline():
    return {
        "outline_editor_id": "outline-1", "brief_id": "brief-1", "report_id": "report-1",
        "decision_id": "decision-1", "strategy_id": "strat-1", "config_id": "config-1",
        "structure_id": "structure-1", "details_to_include_id": "details-1",
        "schema_version": "1.0", "lifecycle_stage": "outline_editor_ready",
        "sections": [{"order": 1, "heading": "Introduction", "level": "H2", "required": True}],
    }


def candidate(video_id="abc123", score=0.8):
    return {
        "youtube_video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": "Insurance basics", "channel_title": "IRL Research",
        "published_at": "2026-01-01T00:00:00Z", "duration_seconds": 300,
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "relevance_score": score, "source": "youtube_api",
    }


def schema():
    return json.loads(Path("shared/schemas/youtube-videos.schema.json").read_text())


def test_default_is_enabled_but_not_required_and_deterministic():
    candidates = [candidate()]
    first = build_youtube_videos_contract(outline_editor=outline(), candidates=candidates)
    second = build_youtube_videos_contract(outline_editor=outline(), candidates=candidates)
    assert first == second
    assert first["youtube_videos"]["max_videos"] == 1
    assert first["youtube_videos"]["videos"][0]["youtube_video_id"] == "abc123"


def test_selects_highest_relevance_deterministically():
    result = build_youtube_videos_contract(outline_editor=outline(), candidates=[candidate("low", .2), candidate("high", .9), candidate("mid", .5)], max_videos=2)
    assert [v["youtube_video_id"] for v in result["youtube_videos"]["videos"]] == ["high", "mid"]


def test_equal_scores_use_video_id_tiebreaker():
    result = build_youtube_videos_contract(outline_editor=outline(), candidates=[candidate("z", .5), candidate("a", .5)], max_videos=2)
    assert [v["youtube_video_id"] for v in result["youtube_videos"]["videos"]] == ["a", "z"]


def test_required_requires_enabled_and_verified_candidate():
    with pytest.raises(ValueError, match="required cannot be true"):
        build_youtube_videos_contract(outline_editor=outline(), required=True, enabled=False, max_videos=0)
    with pytest.raises(ValueError, match="at least one verified candidate"):
        build_youtube_videos_contract(outline_editor=outline(), required=True, enabled=True, max_videos=1, candidates=[])


def test_disabled_requires_zero_max_and_emits_no_videos():
    result = build_youtube_videos_contract(outline_editor=outline(), enabled=False, max_videos=0, candidates=[candidate()])
    assert result["youtube_videos"]["videos"] == []
    with pytest.raises(ValueError, match="max_videos must be zero"):
        build_youtube_videos_contract(outline_editor=outline(), enabled=False, max_videos=1)


def test_rejects_duplicate_video_ids():
    with pytest.raises(ValueError, match="must be unique"):
        build_youtube_videos_contract(outline_editor=outline(), candidates=[candidate("dup"), candidate("dup")])


def test_rejects_non_api_source_and_noncanonical_url():
    bad_source = candidate(); bad_source["source"] = "search_result"
    with pytest.raises(ValueError, match="source must be youtube_api"):
        build_youtube_videos_contract(outline_editor=outline(), candidates=[bad_source])
    bad_url = candidate(); bad_url["url"] = "https://youtu.be/abc123"
    with pytest.raises(ValueError, match="canonical YouTube watch URL"):
        build_youtube_videos_contract(outline_editor=outline(), candidates=[bad_url])


def test_rejects_unknown_candidate_fields():
    item = candidate(); item["unexpected"] = True
    with pytest.raises(ValueError, match="unsupported fields"):
        build_youtube_videos_contract(outline_editor=outline(), candidates=[item])


def test_rejects_wrong_outline_lifecycle():
    source = outline(); source["lifecycle_stage"] = "article_structure_ready"
    with pytest.raises(ValueError, match="outline_editor_ready"):
        build_youtube_videos_contract(outline_editor=source)


def test_does_not_mutate_inputs():
    source = outline(); candidates = [candidate()]
    before_source = copy.deepcopy(source); before_candidates = copy.deepcopy(candidates)
    build_youtube_videos_contract(outline_editor=source, candidates=candidates)
    assert source == before_source
    assert candidates == before_candidates


def test_output_validates_against_schema():
    output = build_youtube_videos_contract(outline_editor=outline(), candidates=[candidate()])
    Draft202012Validator(schema()).validate(output)


@pytest.mark.parametrize("settings", [
    {"enabled": False, "required": False, "max_videos": 1, "videos": [candidate()]},
    {"enabled": False, "required": True, "max_videos": 0, "videos": []},
    {"enabled": True, "required": False, "max_videos": 0, "videos": []},
])
def test_schema_rejects_cross_field_invariant_violations(settings):
    output = build_youtube_videos_contract(outline_editor=outline(), candidates=[candidate()])
    output["youtube_videos"].update(settings)
    with pytest.raises(ValidationError):
        Draft202012Validator(schema()).validate(output)


def test_schema_rejects_unknown_nested_field():
    output = build_youtube_videos_contract(outline_editor=outline())
    output["youtube_videos"]["unexpected"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema()).validate(output)


def test_no_llm_or_markup_fields():
    output = build_youtube_videos_contract(outline_editor=outline())
    forbidden = {"prompt", "llm", "provider", "model", "iframe", "html", "embed", "generated_text"}
    assert forbidden.isdisjoint(output)
