# IRL Production Stabilization Audit v1

## Required fields

- `stabilization_id`
- `schema_version`
- `project_name`
- `production_id`
- `orchestration_id`
- `job_id`
- `run_id`
- `outcome`
- `checks`
- `audit`

## Check fields

The `checks` object contains:

- `article_package`
- `orchestration`
- `production_job`
- `controlled_production`
- `publication_boundary`

Each check contains:

- `status`: `passed` or `failed`
- `message`: non-empty diagnostic message

## Outcome

- `passed`: all stabilization checks passed.
- `blocked`: one or more checks failed.

## Identifiers

- `stabilization_id` must match `^stabilization_[a-f0-9]{16}$`.
- `production_id` must match `^production_[a-f0-9]{16}$`.
- `orchestration_id` must match `^orchestration_[a-f0-9]{16}$`.
- `job_id` must match `^job_[a-f0-9]{16}$`.
- `run_id` must match `^run_[a-f0-9]{16}$`.

## Publication boundary

The audit treats these values as immutable safety requirements:

- `mode=wordpress_draft`
- `publish=false`
- `human_approval_required=true`

An approved human-review state is not interpreted as a WordPress publish command.

## Read-only behavior

The audit consumes existing records and returns a new result. It must not mutate Article Package, Orchestrator, Production Job, or Controlled Production input objects.

## Audit metadata

The audit section is fixed to:

- `method=production_stabilization`
- `version=v1`
- `validation_status=validated`

No credentials or transport secrets are permitted in the result.
