# Architecture

Iron House OS is organized as a modular operating system for civil construction workflows.

## Boundaries

- `frontend`: React application shell and user-facing workflows.
- `backend`: FastAPI application, API boundaries, services, database access, and integration adapters.
- `database`: SQL schema and seed data for local development and review.
- `docs`: Architecture, development, and operational notes.
- `scripts`: Repeatable developer entry points.

## Backend Shape

The backend keeps route registration, configuration, persistence models, and service modules separate. Phase 1 routes return placeholders so the OpenAPI surface is visible without introducing domain behavior too early.

Future AI agents should be implemented as service modules behind explicit application interfaces. Agent actions should write auditable records before they affect project, supplier, bid, or document data.

## Frontend Shape

The frontend starts as a dashboard shell with stable navigation and placeholder module pages. Phase 2 should add real screens inside the existing routes before introducing deeper navigation.

## Data Strategy

The initial schema favors explicit entities and JSONB extension fields where future ingestion or AI-derived metadata needs room to evolve. As workflows mature, important JSON fields should move into typed columns.
