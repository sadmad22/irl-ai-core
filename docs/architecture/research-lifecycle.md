# Research Report Lifecycle

Version: 1.0

---

# Purpose

Defines the lifecycle of a ResearchReport.

Every report must move through the same stages.

No engine may skip a stage.

---

# Lifecycle

Draft

↓

Normalized

↓

Analyzed

↓

Validated

↓

Approved

↓

Published

↓

Archived

---

# Stage Definitions

## Draft

Input received.

Only keyword exists.

---

## Normalized

Keyword normalization completed.

Topic detected.

Language detected.

---

## Analyzed

All analysis services completed.

Intent

SERP

Competition

Entities

Business

Authority

Questions

---

## Validated

Schema validation passed.

Business rules passed.

No required fields missing.

---

## Approved

Decision generated.

Ready for downstream engines.

---

## Published

Immutable.

Cannot be modified.

May only be superseded.

---

## Archived

Historical record.

Read-only.

---

# Allowed Transitions

Draft → Normalized

Normalized → Analyzed

Analyzed → Validated

Validated → Approved

Approved → Published

Published → Archived

---

# Forbidden Transitions

Draft → Published

Draft → Approved

Analyzed → Published

Published → Draft

Archived → Draft

---

# Ownership

Research Engine owns the report until Approved.

SEO Engine receives only Approved reports.

Writer Engine receives only Approved reports.

Publishing Engine receives only Published reports.

---

# Invariants

Published reports are immutable.

Every report has exactly one current state.

Every transition is auditable.

Every transition has timestamp.

Every transition has engine_version.