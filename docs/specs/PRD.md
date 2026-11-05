# Product Requirements Document

## Product overview

Assisted Living Pathfinder is a multi-agent web application that helps older
adults and their families discover, compare, and understand assisted living
options. It also gives facility representatives a way to maintain accurate,
useful listings.

## Core problem

Families struggle to navigate fragmented, hard-to-verify information about
assisted living facilities, including pricing tiers, care levels, licensing,
availability, and amenities. This makes it difficult to compare facilities
confidently or determine whether a facility meets a person's care needs and
budget.

## Goals

- Consolidate facility information into consistent, searchable records.
- Validate important facts against authoritative sources and retain their
  provenance.
- Match natural-language family needs to relevant facilities.
- Explain care, contracts, pricing, and financial structures in accessible
  language.
- Allow facility representatives to submit and maintain their own listings.

## Target actors

### Families and older adults

Search for facilities, compare options, review evidence and freshness, and ask
questions about care and costs.

### Facility representatives

Create and update facility profiles containing:

- Pricing and pricing tiers
- Care levels and policies
- Location and service area
- Amenities
- Licensing details and availability
- Facility photos

Submissions must be validated, and users must be shown whether information is
facility-provided, externally sourced, or independently verified.

## Multi-agent ecosystem

### Ingestion Agent

Scrapes, structures, and validates facility data from external directories and
authorized user submissions. It normalizes source data and records provenance
for later verification.

### Curator/Validator Agent

Cross-references facility details such as state licensing numbers, safety
violations, pricing structures, and record freshness. It flags conflicts for
review and updates validation status without silently replacing source data.

### Search & Matchmaking Agent

Translates natural-language requests into precise vector and relational
database queries. For example: “Find a memory care facility near Bothell under
$6,000 per month with high staff ratios.” Results should explain which criteria
matched and distinguish verified facts from unverified claims.

### Engagement Agent

Answers follow-up questions about contracts, care types, and financial
structures using domain templates and the verified facility record. It should
identify uncertainty and avoid presenting general guidance as legal, medical,
or financial advice.

## Core capabilities

### Facility listing management

- Authenticated facility representatives can create and edit listings.
- Listings capture pricing, policies, location, amenities, care levels,
  licensing, availability, and contact information.
- Representatives can upload, order, caption, and remove photos.
- Changes retain audit history and validation status.

### Validation and trust

- Each material fact records its source, last-checked date, and verification
  status.
- Conflicting or stale data is flagged for review.
- Licensing and safety information is cross-referenced with authoritative state
  sources where available.
- Facility-submitted claims are clearly labeled until verified.

### Search and comparison

- Users can search in natural language and apply structured filters.
- Search supports budget, geography, care level, amenities, availability, and
  other recorded criteria.
- Semantic search uses facility descriptions alongside structured filters.
- Users can compare selected facilities and understand why each result matched.

### Guided engagement

- Users can ask conversational follow-up questions.
- Answers cite the underlying facility facts or domain template where possible.
- The product displays appropriate uncertainty and professional-advice
  disclaimers.

## Non-functional requirements

- **Accessibility:** Target WCAG 2.2 AA with readable typography, keyboard
  navigation, clear language, and touch-friendly controls for older users.
- **Privacy and security:** Enforce role-based access, protect personal and
  facility account data, validate uploads, and keep an audit trail.
- **Reliability:** Agent workflows must be durable, resumable, observable, and
  safe to retry.
- **Transparency:** Preserve source provenance and make verification status and
  data freshness visible.
- **Performance:** Return common filtered searches interactively and move slow
  ingestion or validation work to background jobs.

## Technical stack

- **Version control:** GitHub
- **Agent orchestration:** LangGraph (Python) for stateful, durable, multi-turn
  agent loops
- **LLM engine:** Google Gemini through the `google-genai` SDK for high-context
  reasoning and data extraction
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL with pgvector for structured facility records and
  semantic text search
- **Frontend:** Next.js (React) with Tailwind CSS

## Initial success criteria

- A facility representative can create a complete listing and upload photos.
- A family can search using natural language plus structured constraints and
  receive relevant, explainable results.
- Every displayed facility fact exposes source and freshness information.
- Validation workflows can identify conflicts in licensing, safety, and pricing
  data for review.
- Users can ask follow-up questions while receiving clear citations and
  uncertainty indicators.

## Out of scope for the initial release

- Clinical diagnosis or individualized medical advice
- Legal or financial advice
- Booking, payment processing, or contract execution
- Autonomous publication of unresolved conflicting data
