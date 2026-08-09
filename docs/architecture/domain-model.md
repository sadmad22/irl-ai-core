# IRL AI Core Domain Model

Version: 1.0

---

# Purpose

This document defines the canonical domain model of IRL AI Core.

All engines, contracts, schemas, services, APIs, pipelines, and storage layers MUST follow these domain models.

This document is the Single Source of Truth for the entire system.

---

# Core Principles

- Every engine exchanges structured contracts.
- No engine consumes free-form text from another engine.
- Domain models are implementation-independent.
- JSON Schema, Python models, validators, and APIs are derived from these models.
- Every object has a globally unique identifier.
- Every report is immutable once published.
- Every decision is auditable.

---

# Root Object

ResearchReport

A ResearchReport represents the complete research output for one keyword.

ResearchReport
│
├── Metadata
├── Keyword
├── SearchIntent
├── SearchMetrics
├── SERPAnalysis
├── CompetitorAnalysis
├── EntityAnalysis
├── QuestionAnalysis
├── TopicalAuthority
├── BusinessAnalysis
├── Recommendation
├── Decision
└── Audit

---

# Metadata

Purpose

Stores document information.

Fields

- report_id
- created_at
- version
- engine_version
- language
- country
- author

---

# Keyword

Purpose

Represents the target keyword.

Fields

- keyword
- normalized_keyword
- topic
- category
- niche

---

# SearchIntent

Purpose

Represents search intent.

Allowed values

- informational
- commercial
- transactional
- navigational

---

# SearchMetrics

Purpose

Represents keyword metrics.

Fields

- search_volume
- keyword_difficulty
- cpc
- trend

---

# SERPAnalysis

Purpose

Represents Google search landscape.

Fields

- featured_snippet
- people_also_ask
- videos
- images
- local_pack
- shopping_results

---

# CompetitorAnalysis

Purpose

Represents competing pages.

Fields

- competitors
- average_word_count
- average_authority
- strengths
- weaknesses
- content_gaps

---

# EntityAnalysis

Purpose

Represents important entities.

Fields

- primary_entities
- secondary_entities
- organizations
- products
- locations

---

# QuestionAnalysis

Purpose

Represents user questions.

Fields

- people_also_ask
- faqs
- related_questions

---

# TopicalAuthority

Purpose

Measures how well the keyword fits Insurance Review Lab.

Fields

- authority_score
- cluster
- parent_topic
- supporting_topics

---

# BusinessAnalysis

Purpose

Measures business value.

Fields

- affiliate_potential
- adsense_potential
- conversion_potential
- commercial_value

---

# Recommendation

Purpose

Recommends the best content strategy.

Fields

- content_type
- content_format
- priority
- estimated_effort

---

# Decision

Purpose

Final research decision.

Allowed values

- approved
- rejected
- review

---

# Audit

Purpose

Ensures traceability.

Fields

- validation_status
- validation_errors
- notes

---

# Domain Rules

ResearchReport owns every object.

Keyword belongs to exactly one report.

Decision is generated only after every analysis is complete.

Every report must contain Metadata.

Every report must contain Decision.

Every report must be reproducible.

No service may modify a published report.

---

# Future Engines

Research Engine

Consumes

Keyword

Produces

ResearchReport

SEO Engine

Consumes

ResearchReport

Produces

SEOReport

Writer Engine

Consumes

ResearchReport

Produces

ArticleDraft

Editorial Engine

Consumes

ArticleDraft

Produces

EditorialReview

Publishing Engine

Consumes

EditorialReview

Produces

PublicationPackage