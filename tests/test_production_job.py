from agents.research.production_job import (
    STATUSES,
    STAGES,
    advance_production_job,
    create_production_job,
    fail_production_job,
    job_from_orchestration,
)


def test_create_production_job_has_trackable_initial_state():
    job = create_production_job("m7-consultant-liability", job_id="job_0123456789abcdef")
    assert job == {
        "job_id": "job_0123456789abcdef",
        "schema_version": "1.0",
        "status": "queued",
        "current_stage": None,
        "lineage": {"project_name": "m7-consultant-liability"},
        "error": None,
        "ready_to_publish": False,
        "audit": {
            "method": "production_job_state",
            "version": "v1",
            "validation_status": "validated",
        },
    }


def test_job_id_is_validated():
    try:
        create_production_job("topic", job_id="job_invalid")
    except ValueError as exc:
        assert "job_id" in str(exc)
    else:
        raise AssertionError("invalid job_id should fail")


def test_status_machine_follows_roadmap():
    job = create_production_job("topic", job_id="job_0123456789abcdef")
    job = advance_production_job(job, status="researching", current_stage="research")
    job = advance_production_job(job, status="building", current_stage="intelligence")
    job = advance_production_job(job, status="building", current_stage="configuration")
    job = advance_production_job(job, status="building", current_stage="structure")
    job = advance_production_job(job, status="drafting", current_stage="draft")
    job = advance_production_job(job, status="editing", current_stage="editorial_cleanup")
    job = advance_production_job(job, status="optimizing", current_stage="media")
    job = advance_production_job(job, status="optimizing", current_stage="linking")
    job = advance_production_job(job, status="optimizing", current_stage="optimization")
    job = advance_production_job(job, status="qa", current_stage="qa")
    job = advance_production_job(job, status="ready", current_stage="article_package")

    assert job["status"] == "ready"
    assert job["current_stage"] == "article_package"
    assert job["ready_to_publish"] is True
    assert job["error"] is None


def test_ready_job_can_be_recorded_as_published_without_publishing():
    job = create_production_job("topic", job_id="job_0123456789abcdef")
    job = advance_production_job(job, status="researching", current_stage="research")
    job = advance_production_job(job, status="building", current_stage="intelligence")
    job = advance_production_job(job, status="drafting", current_stage="draft")
    job = advance_production_job(job, status="editing", current_stage="editorial_cleanup")
    job = advance_production_job(job, status="optimizing", current_stage="media")
    job = advance_production_job(job, status="optimizing", current_stage="linking")
    job = advance_production_job(job, status="optimizing", current_stage="optimization")
    job = advance_production_job(job, status="qa", current_stage="qa")
    job = advance_production_job(job, status="ready", current_stage="article_package")
    job = advance_production_job(job, status="published", current_stage=None)
    assert job["status"] == "published"
    assert job["current_stage"] is None
    assert job["ready_to_publish"] is False


def test_invalid_transition_is_rejected():
    job = create_production_job("topic", job_id="job_0123456789abcdef")
    try:
        advance_production_job(job, status="drafting", current_stage="draft")
    except ValueError as exc:
        assert "transition" in str(exc)
    else:
        raise AssertionError("invalid transition should fail")


def test_invalid_stage_for_status_is_rejected():
    job = create_production_job("topic", job_id="job_0123456789abcdef")
    try:
        advance_production_job(job, status="researching", current_stage="draft")
    except ValueError as exc:
        assert "current_stage" in str(exc)
    else:
        raise AssertionError("invalid status/stage pairing should fail")


def test_failure_records_stage_and_preserves_lineage():
    job = create_production_job("topic", job_id="job_0123456789abcdef", production_id="production_0123456789abcdef")
    failed = fail_production_job(
        job,
        stage="draft",
        error_type="DraftError",
        message="Draft generation failed",
    )
    assert failed["status"] == "failed"
    assert failed["current_stage"] == "draft"
    assert failed["lineage"] == {
        "project_name": "topic",
        "production_id": "production_0123456789abcdef",
    }
    assert failed["error"] == {
        "stage": "draft",
        "type": "DraftError",
        "message": "Draft generation failed",
    }
    assert failed["ready_to_publish"] is False


def test_failed_job_is_terminal_for_this_phase():
    job = create_production_job("topic", job_id="job_0123456789abcdef")
    job = fail_production_job(job, stage="research", error_type="ResearchError", message="failed")
    try:
        advance_production_job(job, status="researching", current_stage="research")
    except ValueError as exc:
        assert "transition" in str(exc)
    else:
        raise AssertionError("failed job must not resume through Phase 4 state machine")


def test_orchestration_projection_maps_running_stages():
    orchestration = {
        "orchestration_id": "orchestration_0123456789abcdef",
        "project_name": "topic",
        "lifecycle_stage": "running",
        "current_stage": "editorial_cleanup",
        "article_package": None,
    }
    job = job_from_orchestration(orchestration)
    assert job["status"] == "editing"
    assert job["current_stage"] == "editorial_cleanup"
    assert job["lineage"]["orchestration_id"] == "orchestration_0123456789abcdef"
    assert job["ready_to_publish"] is False


def test_orchestration_projection_maps_completed_to_ready():
    orchestration = {
        "orchestration_id": "orchestration_0123456789abcdef",
        "project_name": "topic",
        "lifecycle_stage": "completed",
        "current_stage": None,
        "article_package": {"production_id": "production_0123456789abcdef"},
    }
    job = job_from_orchestration(orchestration)
    assert job["status"] == "ready"
    assert job["current_stage"] == "article_package"
    assert job["lineage"]["production_id"] == "production_0123456789abcdef"
    assert job["ready_to_publish"] is True


def test_orchestration_projection_maps_failure():
    orchestration = {
        "orchestration_id": "orchestration_0123456789abcdef",
        "project_name": "topic",
        "lifecycle_stage": "failed",
        "current_stage": "qa",
        "article_package": None,
        "error": {"stage": "qa", "type": "QualityGateBlocked", "message": "blocked"},
    }
    job = job_from_orchestration(orchestration)
    assert job["status"] == "failed"
    assert job["current_stage"] == "qa"
    assert job["error"]["type"] == "QualityGateBlocked"
    assert job["ready_to_publish"] is False


def test_constants_match_roadmap():
    assert STATUSES == (
        "queued", "researching", "building", "drafting", "editing",
        "optimizing", "qa", "ready", "published", "failed",
    )
    assert STAGES == (
        "research", "intelligence", "configuration", "structure", "draft",
        "editorial_cleanup", "media", "linking", "optimization", "qa",
        "article_package",
    )
