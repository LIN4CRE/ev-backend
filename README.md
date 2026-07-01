# Ev Backend

Ev is a modular FastAPI backend intended to power an AI voice assistant with Alexa integration.

## Current focus

This stage prioritizes Alexa operational reliability first, then improves overall operational maturity:

- FastAPI application scaffold
- Environment-based configuration with validation
- Structured logging
- Request correlation and request/response logging middleware
- Public health endpoint
- Admin configuration diagnostics endpoint
- Header-based admin authentication foundation
- Admin audit logging
- Basic admin rate limiting
- Alexa webhook endpoint
- Alexa request/response models
- Alexa timestamp validation and optional full signature verification boundary
- Alexa-focused end-to-end reliability tests
- Conversation orchestration service
- Conversation memory abstraction with in-memory, JSON-file, and SQLite persistence
- OpenAI client abstraction with HTTP-based Responses API integration
- Modular tool registry and execution layer
- Home Assistant client abstraction with HTTP implementation and basic spoken-name resolution
- Calendar client abstraction with Google Calendar read-only support
- Web search client abstraction with DuckDuckGo provider support
- Startup diagnostics reporting
- Docker healthchecks
- CI workflow
- Unit tests, linting, and static type checking

## Project structure

```text
app/
  api/routes/          # HTTP route modules
  clients/             # External provider clients
  core/                # Cross-cutting concerns like config, logging, security, rate limiting
  models/              # Request, response, and orchestration models
  services/            # Business logic layer
  validators/          # Request validation boundaries
tests/                 # Unit and integration-style tests
```

## Requirements

- Docker + Docker Compose
- or Python 3.12 locally

## Quick start with Docker

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Start the service:

   ```bash
   docker compose up --build
   ```

3. Test the API:

   - Health: `GET http://localhost:8000/api/v1/health`
   - Admin config: `GET http://localhost:8000/api/v1/admin/config` with header `X-Admin-Api-Key`
   - Admin tools: `GET http://localhost:8000/api/v1/admin/tools` with header `X-Admin-Api-Key`
   - Admin memory sessions: `GET http://localhost:8000/api/v1/admin/memory/sessions` with header `X-Admin-Api-Key`
   - Alexa webhook: `POST http://localhost:8000/api/v1/alexa/webhook`

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Quality checks

```bash
make check
```

This runs:
- Ruff linting
- mypy type checking
- pytest

## Environment variables

Key variables include:

- `ADMIN_API_KEY`
- `ALEXA_SKILL_ID`
- `ALEXA_REQUEST_TOLERANCE_SECONDS`
- `REQUIRE_ALEXA_SIGNATURE_HEADERS`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `HOME_ASSISTANT_URL`
- `HOME_ASSISTANT_TOKEN`
- `CALENDAR_PROVIDER`
- `GOOGLE_CALENDAR_API_KEY`
- `GOOGLE_CALENDAR_ID`
- `WEB_SEARCH_PROVIDER`
- `MEMORY_BACKEND` (`memory`, `file`, or `sqlite`)
- `MEMORY_FILE_PATH`
- `MEMORY_SQLITE_PATH`

## Alexa reliability notes

- The Alexa webhook path is now covered by focused end-to-end style tests.
- Request logging middleware emits a request ID and returns it as `X-Request-Id`.
- Startup diagnostics log whether Alexa-related configuration is active.
- Docker healthchecks now verify API readiness through the health endpoint.
- A starter Alexa skill package is included under `alexa/`.
- Local automation validates the Alexa manifest and interaction model.

## Alexa skill package

Yes — you need an actual Alexa skill for the backend to be reachable by Alexa.

This repository now includes a starter skill package:

- `alexa/skill-package/skill.json`
- `alexa/skill-package/interactionModels/custom/en-GB.json`
- `alexa/README.md`

A short development-only Alexa voice command is also included:
- `PrepIntent`
- memorable utterances: `prep`, `ready`, `sync`
- short invocation name: `ev bot`

Useful commands:

```bash
make doctor
make alexa-generate
make alexa-validate
make alexa-sync
make alexa-ready
make alexa-local-dev
```

Important:
- Alexa cannot reach `localhost` directly.
- You must expose the backend on a public HTTPS URL and set that URL in the skill manifest.
- `make doctor` checks local tooling, critical files, and endpoint assumptions.
- `make alexa-sync` can automatically detect a local ngrok HTTPS tunnel and wire it into the skill manifest.
- `make alexa-local-dev` can attempt to detect or start ngrok, sync the Alexa endpoint, validate the package, and print a ready summary.

## CI

A GitHub Actions workflow is included at:

- `.github/workflows/ci.yml`

It runs the full `make check` pipeline on pushes and pull requests.

## Next suggested stage

The next stage should add:

- richer Alexa intent coverage and schema tests
- provider-backed integration test fixtures and mocks
- background job handling for slower tools
- improved Home Assistant natural entity mapping
- optional JWT or OAuth admin auth when needed later

## Notes

- Secrets are configured through environment variables.
- The current admin authentication remains intentionally simple and can be upgraded later.
