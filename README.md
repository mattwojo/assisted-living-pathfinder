# Assisted Living Pathfinder

Assisted Living Pathfinder is a multi-agent web application that helps families
find and evaluate assisted living facilities using structured, verifiable
information.

This is a local-development prototype. It includes a Next.js interface for
searching and comparing listings, asking questions, and managing community
profiles and photos. Reviewers can inspect and update fact statuses. See the
[product requirements](docs/specs/PRD.md) and [task breakdown](docs/TASKS.md)
for the broader planned scope.

## Run locally

Requirements: Python 3, Node.js 20.9 or later, and npm.

From the repository root, set up and start the API:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

In another terminal, start the frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The frontend proxies
`/api` to `http://127.0.0.1:8000`; set `PATHFINDER_API_URL` before starting
Next.js if the backend is elsewhere.

On first startup the backend creates a local SQLite database and fictional
sample communities. Demo accounts use password `pathfinder`:
`family@example.com`, `rep@example.com`, and `admin@example.com`. The
representative account can edit its sample listings; the admin can review
facts. New family and representative accounts can also be created in the app.
Data and uploaded files default to `backend/data/`; set `PATHFINDER_DB` and
`PATHFINDER_UPLOADS` to change those paths.

**Do not deploy this prototype as-is or enter sensitive information.** It
seeds known demo credentials, uses local storage and development-oriented
authentication, and has not undergone production security or accessibility
review. Sample listings and their verification statuses are fictional. Submitted
listings are visible in search before review; verify details independently.
The search agent uses rules and a limited list of nearby cities, not a
production geospatial or semantic search. Use the city filter for cities the
natural-language parser does not recognize. Answers are general information,
not medical, legal, or financial advice.

To run checks:

```bash
python -m unittest discover -s tests -v
cd frontend
npm test
npm run build
```

## Stack

- **Agents:** LangGraph; optional Google Gemini wording via the `google-genai` SDK
- **Backend:** FastAPI
- **Data:** SQLite for local development; PostgreSQL with pgvector is planned
- **Frontend:** Next.js and React

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
