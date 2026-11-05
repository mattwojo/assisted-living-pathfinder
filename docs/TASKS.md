# Implementation tasks

## Foundation

- [ ] Define architecture, environments, and local development workflow.
- [ ] Add backend and frontend linting, testing, and CI workflows.
- [ ] Define shared accessibility, privacy, security, and observability
      requirements.

## Data and backend

- [ ] Design facility, pricing, care, policy, amenity, licensing, availability,
      source, and validation schemas.
- [ ] Configure PostgreSQL and pgvector migrations.
- [ ] Implement authentication and role-based access for facility
      representatives and administrators.
- [ ] Implement FastAPI endpoints for facility listing creation and updates.
- [ ] Implement validated photo upload, storage, metadata, ordering, and
      deletion.
- [ ] Record provenance, verification status, freshness, and audit history.

## Agents

- [ ] Define shared LangGraph state, retry, approval, and error-handling
      patterns.
- [ ] Implement the Ingestion Agent and source adapters.
- [ ] Implement the Curator/Validator Agent and conflict-review workflow.
- [ ] Implement the Search & Matchmaking Agent with hybrid relational and vector
      queries.
- [ ] Implement the Engagement Agent with citations, uncertainty handling, and
      domain templates.
- [ ] Add agent evaluation datasets and regression tests.

## Frontend

- [ ] Build accessible facility onboarding and listing-management flows.
- [ ] Build photo upload and management interfaces.
- [ ] Build natural-language search and structured filters.
- [ ] Build explainable results, facility details, and comparison views.
- [ ] Build conversational follow-up questions with source citations.
- [ ] Test core flows against WCAG 2.2 AA criteria.

## Release readiness

- [ ] Add end-to-end tests for listing, validation, search, and engagement.
- [ ] Add monitoring for APIs, background jobs, and agent workflows.
- [ ] Complete threat modeling, privacy review, and upload security testing.
- [ ] Document deployment, backup, restoration, and incident-response
      procedures.
