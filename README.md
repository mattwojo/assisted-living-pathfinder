# Assisted Living Pathfinder

Assisted Living Pathfinder is a multi-agent web application that helps families
find and evaluate assisted living facilities using structured, verifiable
information.

The project is in its initial planning and scaffolding phase. See the
[product requirements](docs/specs/PRD.md) and [task breakdown](docs/TASKS.md)
for the planned scope.

## Planned stack

- **Agents:** LangGraph and Google Gemini via the `google-genai` SDK
- **Backend:** FastAPI
- **Data:** PostgreSQL with pgvector
- **Frontend:** Next.js, React, and Tailwind CSS

## Repository structure

```text
.
├── .github/workflows/  # CI/CD workflows
├── agents/             # Agent definitions and graphs
├── backend/            # FastAPI services
├── docs/
│   ├── specs/          # Product and architecture specifications
│   └── TASKS.md        # Implementation task breakdown
└── frontend/           # Next.js application
```
