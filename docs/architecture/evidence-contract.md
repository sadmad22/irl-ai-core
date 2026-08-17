# Research Evidence Contract

Version: 1.0

## Purpose

The Evidence Contract is the canonical representation of a traceable research observation or derived finding.

Evidence is not an analyzer output, recommendation, or decision. It is the structured unit that records what the system knows, what claim the value supports, where it came from, how it was derived, and how confident the system is in that evidence.

## Architectural Position

```text
Research Sources
      ↓
   Analyzers
      ↓
 Evidence Contract
      ↓
 ResearchReport
      ↓
 Validation
      ↓
 Recommendation
      ↓
 Decision
```

## Core Invariants

1. Every evidence item has a globally unique `evidence_id`.
2. Every evidence item belongs to exactly one `report_id`.
3. Evidence never directly creates a decision.
4. Evidence must retain source and provenance information.
5. Derived evidence must reference its upstream evidence through `derived_from`.
6. Confidence is normalized to the range 0..1.
7. Evidence status is independent from the ResearchReport lifecycle state.
8. The `domain` field remains extensible so future Entity, Question, Business, Authority, Topic, and Content evidence can use the same contract.
9. Analyzer names identify provenance only; they do not define the domain contract.
10. Published ResearchReports remain governed by the Research Report Lifecycle; Evidence does not introduce alternative report states.

## Evidence Types

### observation

A directly observed fact from a source or source-backed analysis.

### derived

A finding calculated or inferred from one or more upstream evidence items.

### comparison

A finding produced by comparing multiple observations or derived findings.

### contradiction

Evidence that conflicts with, or materially challenges, another claim.

## Domains

The contract intentionally does not hard-code a domain enum. Current and planned domains include:

- `intent`
- `serp`
- `competition`
- `entity`
- `question`
- `business`
- `authority`
- `topic`
- `content`

New domains can be introduced without changing the Evidence object structure.

## Claim Model

Each evidence item expresses a claim as:

```text
subject + claim.type + claim.attribute + value
```

Example:

```json
{
  "subject": {
    "type": "keyword",
    "id": "kw_expat-health-insurance"
  },
  "claim": {
    "type": "query_intent",
    "attribute": "primary_intent"
  },
  "value": {
    "type": "categorical",
    "data": "Informational"
  }
}
```

## Provenance

`source` answers **where the underlying information came from**.

`provenance` answers **which engine and method produced this evidence**.

This separation allows analyzer implementations to evolve without changing the domain contract.

## Evidence Lineage

Derived evidence must use `derived_from` to reference upstream evidence IDs.

```text
SERP observations
      ↓
SERP intent evidence
      ↓
Intent alignment evidence
      ↓
Strategy signal evidence
```

This creates an auditable evidence lineage that can later support Recommendation and Decision layers.

## Lifecycle Relationship

Evidence is produced during the ResearchReport `Analyzed` stage and is validated before the report can move to `Approved`.

```text
Draft
  ↓
Normalized
  ↓
Analyzed  ← Evidence generated
  ↓
Validated ← Evidence contract and references checked
  ↓
Approved
  ↓
Published
  ↓
Archived
```

Evidence does not replace or modify the ResearchReport lifecycle.

## Future Compatibility

The same contract is intended to support future evidence such as:

- Entity presence and relevance
- Question frequency and coverage
- Business/commercial value
- Authority and topical fit
- Content coverage and content gaps

Those domains should add new claim types and attributes without creating separate evidence schemas.
