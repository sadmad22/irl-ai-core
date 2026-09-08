# IRL AI Core — Production Architecture v1

Version: 1.0  
Status: **Architecture Locked for Phase 1**

---

## 1. Purpose

This document defines the production architecture for running **IRL AI Core** as a controlled content-production system for **Insurance Review Lab (IRL)**.

The architecture is intentionally limited to the minimum structure required to move from the completed Core implementation to production operation.

It does **not** implement the Production Contract, Production Orchestrator, Production Job State, WordPress Connector, or production automation. Those are subsequent implementation phases.

---

## 2. Existing Architectural Foundation

IRL AI Core already follows a contract-driven architecture in which engines exchange structured objects rather than free-form text. The canonical domain model is implementation-independent and is the source for models, schemas, validators, APIs, and storage. Published research reports are immutable and decisions are auditable.

The existing ResearchReport lifecycle is:

```text
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
```

No production architecture introduced here may bypass or replace this existing research lifecycle.

---

## 3. Production System Boundary

The production system has three principal boundaries:

```text
┌─────────────────────────────────────────────────────────┐
│                    IRL AI CORE                          │
│                                                         │
│  Research → Intelligence → Configuration → Content      │
│  → Editorial → Media → Linking → Optimization → QA     │
│                                                         │
└────────────────────────┬────────────────────────────────┘
                         │
                  Production Output
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              WORDPRESS CONNECTOR                        │
│                                                         │
│  Transport / mapping / Draft creation / Media transfer │
│                                                         │
└────────────────────────┬────────────────────────────────┘
                         │
                    WordPress API
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 IRL WEBSITE                             │
│                                                         │
│              WordPress on Hostinger                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Boundary rule

**IRL AI Core owns content-production decisions. WordPress owns content management and publication.**

The WordPress Connector is an integration boundary, not a second content-production engine.

---

## 4. Responsibilities

### 4.1 IRL AI Core

IRL AI Core is responsible for producing the validated content-production result.

Its responsibilities include the capabilities already implemented across the roadmap, including:

- Research
- Content Score
- Semantic / NLP Keywords
- SERP / Competitor Analysis
- Article Configuration & Structure
- Article Type
- Article Size / Heading Targets
- Target Country
- AI Images
- Informative Alt Text
- Image Style / Brand Visual Style
- Image Placement / Media Strategy
- Tone of Voice
- Point of View
- Readability
- Editorial Cleanup
- Humanization through Editorial Cleanup
- Model Router
- Brand Voice
- Details to Include
- Outline Editor
- Italics
- YouTube Videos
- External Linking
- Internal Linking
- Content Optimization / Gap Analysis
- Real-Time News
- QA and validation already provided by the applicable layers

The production architecture does not create duplicate versions of these capabilities.

### 4.2 WordPress Connector

The connector will later translate an approved production output into WordPress operations.

Its architectural responsibilities are limited to:

- authentication boundary
- request/response transport
- mapping production output to WordPress fields
- creating or updating Draft content
- transferring approved media
- assigning supported taxonomy and metadata
- returning WordPress identifiers and operation status

It must not:

- perform research
- select content strategy
- rewrite article content
- invent facts
- choose SEO targets
- make editorial decisions
- bypass Core validation
- publish automatically during the initial controlled-production phase

### 4.3 WordPress / Hostinger

WordPress remains the website's CMS and publication environment.

Hostinger remains the hosting environment for the live Insurance Review Lab WordPress installation.

The production architecture does not move the Core into WordPress.

---

## 5. Production Flow

The target production flow is:

```text
Article Request
      ↓
Production Job
      ↓
IRL AI Core
      ↓
Research & Intelligence
      ↓
Article Configuration & Structure
      ↓
Content Production
      ↓
Editorial / Humanization
      ↓
Media
      ↓
Linking
      ↓
Optimization
      ↓
QA / Validation
      ↓
Production Output
      ↓
WordPress Connector
      ↓
WordPress Draft
      ↓
Human Review
      ↓
Publish
```

The detailed structure of **Production Output / Article Package** is deliberately deferred to Phase 2.

---

## 6. Control Points

The production architecture contains four essential control points.

### Control Point A — Input

A production request must identify the article/job being requested and provide the information required by the existing Core pipeline.

### Control Point B — Core Validation

The Core must complete the applicable contracts, invariants, and QA checks before production output is considered ready for WordPress.

### Control Point C — WordPress Boundary

Only a validated production output may cross into the WordPress Connector.

### Control Point D — Human Publication Approval

During initial production operation, the WordPress result remains a Draft until human review is completed.

```text
Input
  ↓
Core
  ↓
Validated Output  ← Control Point
  ↓
WordPress Draft  ← Control Point
  ↓
Human Approval   ← Control Point
  ↓
Publish
```

---

## 7. Data Flow Principles

### Structured exchange

Production components exchange structured contracts.

### Lineage preservation

Existing lineage identifiers must remain available across downstream production stages wherever the applicable contract defines them.

### No hidden transformation

A downstream boundary must not silently alter validated content or metadata.

### Deterministic behavior

Existing deterministic IDs, ordering, validation, and contract behavior remain authoritative.

### Immutable research history

The production layer must not modify a published ResearchReport. Updates create new downstream production results rather than mutating historical research records.

---

## 8. Failure Boundary

A production failure belongs to the stage where it occurs.

```text
Stage Failure
     ↓
Stop current production job
     ↓
Record failure state
     ↓
Preserve completed outputs
     ↓
Retry / resume from an appropriate boundary
```

A failed WordPress operation must not require rerunning research unless a later phase explicitly establishes that dependency.

A Core validation failure must prevent the output from crossing the WordPress boundary.

Detailed retry semantics are deferred until the Production Job implementation phase.

---

## 9. Security Boundary

Credentials required for external services must remain outside source-controlled code and repository content.

The WordPress authentication mechanism belongs to the integration boundary and must not become part of the content contracts.

No production architecture component may require storing secrets in Git.

---

## 10. Deployment Model

The production architecture intentionally separates development from the live website:

```text
GitHub / Codespaces
        │
        │ develop + test
        ▼
IRL AI Core
        │
        │ production execution
        ▼
WordPress Connector
        │
        ▼
WordPress on Hostinger
```

GitHub Codespaces remains the development and validation environment.

Hostinger remains the WordPress hosting environment.

No direct modification of the live WordPress site is part of Phase 1.

---

## 11. Explicit Non-Goals for Phase 1

Phase 1 does not implement:

- ArticlePackage fields or schema
- Production Orchestrator code
- Production Job State code
- WordPress Plugin code
- WordPress API calls
- automatic publishing
- production dashboard
- scheduling system
- multi-site support
- new AI/content features
- new external providers
- new dependencies

These items are intentionally excluded to keep the architecture stable and the implementation sequence controlled.

---

## 12. Phase 1 Completion Criteria

Phase 1 is complete when the following architectural decisions are fixed:

1. IRL AI Core remains the content-production engine.
2. WordPress remains the CMS and publication environment.
3. Hostinger remains the website hosting environment.
4. A dedicated WordPress Connector forms the integration boundary.
5. Validated Core output is the only content allowed across that boundary.
6. Initial WordPress delivery creates Draft content for human approval.
7. Existing ResearchReport lifecycle and contract-driven architecture remain intact.
8. Production output contract details are deferred to Phase 2.
9. No unnecessary production infrastructure is introduced.

---

## 13. Next Phase

After this architecture is accepted and validated, implementation proceeds to:

> **Phase 2 — Article Production Contract**

The next phase defines the exact structure, fields, enums, invariants, and schema of the production output consumed by the future WordPress Connector.
