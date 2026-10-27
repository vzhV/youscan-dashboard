# CLAUDE.md

Guidance for anyone (human or agent) working in this repository. Follow it exactly. When a rule here conflicts with
habit, the rule wins. When something isn't covered, choose the simplest option that is consistent with the code
around it.

## What this is

A full-stack dashboard app built as the YouScan full-stack test task (`task-description.md`). The dashboard shows
widgets three per row: line, bar, stacked bar, pie and text.

- The initial charts are **parsed from the provided `.xlsx` and `.csv` files** through a reusable import mechanism.
  Hardcoding that data is forbidden.
- Users can:
  - create widgets (charts get random data)
  - rename them
  - edit text widgets (the change persists after a reload)
  - delete widgets
  - reset the board to its seeded state
  - import new files through a two-step upload page, the API (Swagger) or the CLI
- Every widget has its own loading and error states.

The work is graded on **architecture, code style, complexity and decomposition**. Simple and consistent beats clever.

## Stack

| Area | Choice |
|---|---|
| Frontend | React (latest) + TypeScript (strict) + Vite, Ant Design (**only** UI kit: no MUI), TanStack Query v5, React Router, Chart.js 4 + react-chartjs-2, `openapi-typescript` + `openapi-fetch` |
| Backend | Python 3.12, FastAPI, Pydantic v2 + pydantic-settings, SQLAlchemy 2 (async) + psycopg 3, Alembic, openpyxl, Typer |
| Database | PostgreSQL 17 (local: docker compose; production: Supabase via the Supavisor pooler) |
| Hosting | Vercel: two projects (`frontend/`, `backend/`) in one monorepo |
| Tooling | uv, Ruff, mypy, import-linter, pytest · pnpm, ESLint, Prettier, Vitest, Testing Library, MSW, Playwright · pre-commit · Makefile |

## Repository layout

```
/                         Makefile, docker-compose.yml, .pre-commit-config.yaml, .nvmrc, README.md, CLAUDE.md
backend/
  app/
    main.py               create_app() + module-level `app` (Vercel entrypoint)
    core/                 config.py (Settings), db.py (engine, session_scope), errors.py (domain errors), logging.py
    api/                  router.py, deps.py, errors.py (handlers + error_responses()), openapi.py, routes/*.py
    schemas/              Pydantic API contract (WidgetCreate / WidgetUpdate / WidgetRead, …)
    models/               SQLAlchemy ORM models
    repositories/         protocols.py + one repository per aggregate (queries only)
    services/             business logic; seed.py holds the seed manifest
    importing/            PURE: table model, parsers/ (base, csv, xlsx, registry), shaping/ (columns, shaper, chart_rules, suggest)
    charts/               PURE: chart_data.py (ChartData), random_data.py, thinning.py (LTTB)
    cli.py                Typer CLI: inspect, import, seed, stress-seed
  seed_data/              the provided sample files (imported by `seed` and by Reset)
  migrations/             Alembic
  tests/                  unit/, integration/, e2e/, fakes.py, factories.py, fixtures/files/
frontend/
  src/
    app/                  App, router, providers (QueryClient, ConfigProvider), layout
    pages/                thin route components: compose features, no logic
    features/
      dashboard/          grid, Create widget menu, Reset button
      widgets/            card, title, states, error boundary, registry.ts, types/{line,bar,stacked-bar,pie,text}/
      datasets/           two-step upload wizard, datasets table
    shared/               api/ (client, generated schema.d.ts, ApiError, demoMode), ui/, hooks/, lib/, config/
    test/                 setup, msw/, factories, renderWithProviders
  e2e/                    Playwright specs/ and perf/
```

## Commands

Always use the root `Makefile` targets, which wrap uv and pnpm. Don't invent ad-hoc command lines when a target
exists.

| Target | What it does |
|---|---|
| `make install` | Install backend (uv) and frontend (pnpm) dependencies and the pre-commit hooks |
| `make dev-db` | Start local Postgres (`dashboard` + `dashboard_test` DBs) |
| `make migrate` / `make seed` | Apply Alembic migrations / import the seed files |
| `make dev` | Run backend (uvicorn :8000) and frontend (Vite, proxies `/api` → :8000) |
| `make format` / `make lint` / `make typecheck` | Ruff format + Prettier / Ruff, ESLint, import-linter / mypy + `tsc --noEmit` |
| `make test` | Unit + integration tests for both apps, with coverage gates |
| `make test-e2e` / `make test-perf` | Playwright full-stack e2e / performance suite |
| `make gen-api` | Regenerate `frontend/src/shared/api/schema.d.ts` from the backend OpenAPI schema |
| `make check` | Everything CI runs. Must pass before any commit |

Node version comes from `.nvmrc` (Node 24 LTS). Python is 3.12, managed by uv.

## Architecture rules

### Backend layers

| Package | Responsibility | May import |
|---|---|---|
| `api/routes` | HTTP only: validate the request, call **one** service method, return a schema | services, schemas, `api.deps`, `api.errors` |
| `services` | Business rules and orchestration. **Never imports FastAPI** | repository protocols, importing, charts, schemas, core |
| `repositories` | SQLAlchemy queries only. `flush()` yes, **`commit()` never** | models, `core.db` |
| `models` | ORM classes | `core.db` base |
| `importing`, `charts` | Pure logic. **No I/O, no SQLAlchemy, no FastAPI** | stdlib, openpyxl, pydantic |
| `core` | Settings, engine/session, domain error types, logging | — |

- **import-linter enforces these imports in CI.** Never import upward.
- **ORM objects never leave the service layer.** Services return Pydantic schemas, and every route declares a
  `response_model`.
- **One transaction per request.** `session_scope()` commits on success, rolls back on error, and always closes. The
  FastAPI dependency and the CLI both use it, and no other code commits.
- **Services depend on repository protocols.** Unit tests inject the in-memory fakes from `tests/fakes.py`.
- **Async everywhere.** CPU-bound parsing runs in a worker thread (`anyio.to_thread`).
- **Config is read only through `core.config.Settings`.** `os.environ` appears nowhere else.

### Database and pooling

- There is one `AsyncEngine` per process. The app lifespan creates it and disposes of it on shutdown.
- Pool settings: `pool_size`/`max_overflow` come from settings (default 5/5), with `pool_pre_ping=True` and
  `pool_recycle=300`.
- When `DB_DISABLE_PREPARED_STATEMENTS=true` (required behind the Supabase transaction pooler on :6543), pass
  `connect_args={"prepare_threshold": None}`.
- Alembic connects through `MIGRATIONS_DATABASE_URL` (Supabase session pooler on :5432).
- Migrations are autogenerated, then **reviewed by hand**. Every migration has a working `downgrade()`, applied
  migrations are never edited, and constraint names follow the metadata naming convention.

### Data model

- **`datasets`** have these columns:
  - `name`
  - `origin` (`seed | upload | generated`)
  - `chart_type`
  - `source_filename`
  - `source_sheet`
  - `row_count`
  - `data` (full `ChartData`, JSONB)
  - `display_data` (thinned to ≤ 1,000 categories at write time)
- **`widgets`** have these columns:
  - `type` (`line | bar | stacked_bar | pie | text`)
  - `title`
  - `position`
  - `dataset_id` (FK, `ON DELETE CASCADE`)
  - `text_content`
- A CHECK constraint enforces "text ⇔ no dataset".
- Every chart widget reads data through its dataset. A random chart owns a `generated` dataset, which is deleted
  along with the widget.
- `ChartData = {categories: list[str], series: list[{name, values: list[float | None]}]}`. All four chart types use
  this shape, and `None` means a gap.

### Import engine (parse → shape → validate)

- **`FileParser` protocol** (`extensions`, `parse(bytes) -> list[Table]`). It has CSV and XLSX implementations and a
  registry keyed by extension. A new format means one class and one registry entry.
- **Column kinds** are `date`, `number` or `text`, determined from every non-empty cell. `id` columns and fully empty
  columns are ignored.
- **Long format** (exactly one date, one text and one number column): pivot it so dates become categories and text
  values become series.
- **Wide format:** one category column (date, otherwise the first text column) plus one series per number column.
- **No silent data loss.** An unused column makes the sheet not shapeable. The 422 error names the first offending
  cell (`column`, `row`, `value`).
- **Duplicates** (a repeated category, or a repeated date + series pair) are rejected.
- **Chart rules:**
  - pie: exactly one series, values ≥ 0, ≤ 20 categories
  - bar and stacked bar: ≤ 100 categories
- **Suggestion order:** line if the categories are dates; pie if there is one series; otherwise stacked bar.
- **Limits:** 4 MB per file (`MAX_UPLOAD_MB`), 100k rows per sheet, 50 columns, 20 sheets.

### HTTP API

- Every route is under `/api/v1`. Swagger is served at `/api/v1/docs`, plus `/api/v1/redoc` and
  `/api/v1/openapi.json`.
- **One error body everywhere:** `{"error": {"code": "<snake_case>", "message": "...", "details": ... | null}}`.
  - Domain errors map to HTTP in `api/errors.py` and nowhere else.
  - Status codes: 404, 409, 413, 415, 422, and a 500 that never leaks internals.
- **Swagger is generated from code.**
  - Every route needs `summary`, `tags`, `response_model`, `status_code` and `responses=error_responses(...)`.
  - The route docstring becomes the operation description.
  - Every schema field needs `Field(description=..., examples=[...])`.
  - Operation IDs come from the custom ID function, e.g. `widgets-update`.
  - The OpenAPI completeness test fails the build if any of this is missing.
- **Same-origin API.** The frontend always calls the relative path `/api/v1`: the Vite proxy handles it locally and
  the Vercel rewrite in production. There is **no CORS**. Don't add it.

### Frontend

- **Layers:** `app → pages → features → shared`.
  - A feature may import another feature only through its `index.ts`.
  - Deep imports and cycles are not allowed; ESLint enforces both.
- **Server state lives only in TanStack Query.**
  - No global store.
  - No `useEffect` data fetching.
  - Query keys come from one factory per feature.
- **No `fetch` in components.**
  - All HTTP goes through `shared/api/client.ts`, the typed `openapi-fetch` client.
  - Errors are normalized into `ApiError {status, code, message, details}`.
  - `schema.d.ts` is generated by `make gen-api` and never edited by hand. CI fails if it is stale.
- **Widget registry** (`features/widgets/registry.ts`) is the only place that knows widget types. Adding a type takes
  one folder plus one registry line. No `switch (type)` anywhere else.
- **Components render; hooks hold the logic.**
  - Props are typed with `type`. No `React.FC`.
  - No prop drilling deeper than 2 levels.
- **Every widget has its own error boundary,** and its own loading, error and Retry states.
- **Styling:** Ant Design components and theme tokens through `ConfigProvider`, plus CSS Modules for custom layout.
  No inline styles except dynamic values.
- **Demo mode** (`?demo=slow|fail`) is a single `openapi-fetch` middleware in `shared/api/demoMode.ts`, and it affects
  only widget data requests. No other code may know about it.

### Performance (the UI must never freeze)

Budgets: a 200-widget board with line datasets up to 100k rows must never block the main thread for more than
**100 ms**, and the first row must appear within **1.5 s** on a local production build. The Playwright perf suite
enforces this.

- Widget data is fetched, and the chart mounted, **only when the card is near the viewport** (`useInView`). Once
  mounted, a chart stays mounted.
- The browser never receives more than `display_data` (≤ 1,000 categories, thinned on the server).
- Chart.js settings:
  - canvas rendering
  - `normalized: true`
  - animations off for large data
  - fixed card height with `maintainAspectRatio: false`
- Mutations update the cache narrowly (append, replace one item, remove one item), so unchanged widgets keep their
  identity. `WidgetCard` is wrapped in `React.memo`.
- Chart.js, the chart bodies and the Datasets route are lazy-loaded.

## Code style

### Hard limits (lint-enforced; generated files and Alembic `versions/` excluded)

| Rule | Limit |
|---|---|
| File length | ≤ 250 lines (aim for < 150) |
| React component file | ≤ 150 lines |
| Function length | ≤ 40 lines (aim for < 20); Ruff max statements 30 |
| Cyclomatic complexity | ≤ 8 |
| Parameters | ≤ 4, otherwise pass an object or dataclass |
| Nesting depth | ≤ 3 |

### General

- **Single responsibility** per module, class and function.
- **Use early returns.** Never `else` after `return`.
- **Naming:** descriptive, with no abbreviations.
  - Booleans: `is/has/can…`
  - Functions: verbs
  - Python files: `snake_case.py`
  - React components: `PascalCase.tsx`
  - Hooks: `useThing.ts`
  - Everything else in TypeScript: `camelCase.ts`
- **No magic numbers or strings.** Use named constants.
- **No dead or commented-out code,** and no `print` or `console.log` in app code. Use logging on the backend.
- **Comments say *why*, not *what*.** Write docstrings only where behavior isn't obvious, plus route docstrings, which
  feed Swagger.
- **KISS and YAGNI.** Extract duplication on the third repetition.
- **Abstractions must earn their place:** they need **two or more real implementations**, or they wrap I/O for tests.
  - No DI containers.
  - No event buses.
  - No generic base repositories.
- **Strict types:**
  - `mypy --strict` and TS `strict` + `noUncheckedIndexedAccess` + `noImplicitOverride`
  - No `any`
  - `# type: ignore[code]` and `as` casts only with a stated reason, and only at system edges
- **Prefer immutable data:** frozen dataclasses, `readonly`.
- **Fail fast. Never swallow errors.**
- **Accessibility:**
  - labelled inputs
  - a keyboard-usable inline editor
  - `jsx-a11y` lint rules
  - tests that find elements by role or label

### Formatting and linting

- **Python:**
  - formatted with `ruff format`
  - linted with Ruff, rule sets `E W F I N UP B A C4 SIM RET PL PT ERA T20 ASYNC S TID C90`
  - type-checked with `mypy --strict` and the pydantic plugin
- **TypeScript:**
  - formatted with Prettier
  - linted with ESLint flat config: typescript-eslint `strict-type-checked` + `stylistic-type-checked`, react,
    react-hooks, jsx-a11y, and import (order, no-cycle, no-restricted-paths)
- **Never weaken a rule to get green.** If a rule truly doesn't fit, disable it on that one line with a reason.

## Testing

| Level | Backend (pytest) | Frontend |
|---|---|---|
| Unit | importing, charts, services with in-memory fakes, settings | utils, chart adapters, hooks, components (Vitest + Testing Library) |
| Integration | repositories, migrations up/down/up, every route via `httpx.AsyncClient` against **real Postgres**; each test rolled back; OpenAPI completeness test | pages and flows against **MSW** |
| E2E | black-box: CLI `seed`/`import` and full HTTP scenarios on a fresh migrated DB | **Playwright** on the full stack. Each test resets the board first. Errors are forced via `page.route` and `?demo=fail` |
| Perf | — | Playwright `perf` project (`stress-seed`, long-task budget) |

- **Write tests first** for services, importing and charts. Use the `superpowers:test-driven-development` skill.
- **One behavior per test,** arranged as setup → action → check, and named after the behavior.
  - Python: `test_<unit>_<condition>_<result>`
  - TypeScript: `it("shows an error state when the data request fails")`
- **Deterministic:** inject a seeded `random.Random`, freeze time, and build data with factories.
- **Fake only at boundaries:** repository fakes, MSW and `page.route`. Never mock code we own.
- **Parser tests** use the real `seed_data/` files plus the edge-case fixtures in `tests/fixtures/files/`.
- **Coverage gates:** backend ≥ 90% (lines and branches), frontend ≥ 85% lines.

## Configuration

- **Backend:** every variable is listed and explained in `backend/.env.example`:
  - `ENVIRONMENT`
  - `DATABASE_URL`
  - `MIGRATIONS_DATABASE_URL`
  - `TEST_DATABASE_URL`
  - `DB_POOL_SIZE`
  - `DB_MAX_OVERFLOW`
  - `DB_DISABLE_PREPARED_STATEMENTS`
  - `MAX_UPLOAD_MB`
  - `LOG_LEVEL`

  `Settings` validates them at startup and refuses to start with an error naming the bad variable.
- **Frontend:** `frontend/.env.example` holds only `API_PROXY_TARGET`, used by the Vite dev/preview proxy.
- **Real `.env` files are never committed.** Only the `.env.example` files are.

## Deployment facts (verified 2026-10-27)

- **Vercel request and response bodies are capped at 4.5 MB** each. Keep payloads small, and keep uploads at 4 MB or
  less.
- **The Vercel Python bundle limit is 500 MB.** The FastAPI app runs as one function on Fluid compute, in the default
  region `iad1`.
- **Supabase is in us-east-1.**
  - The app connects through the transaction pooler on port **6543**, with prepared statements **off**.
  - Migrations go through the session pooler on port **5432**.
  - The direct DB host is IPv6-only, so it is never used from Vercel.
- **Production migrations** run in the backend Vercel build when `MIGRATIONS_DATABASE_URL` is set, which only happens
  in the Production environment.
- **Supabase Free pauses after 7 days of inactivity.** A daily GitHub Actions workflow pings `/api/v1/health`.

## Workflow

1. Brainstorm → design → plan, each reviewed by the user before moving on.
2. Then, **for each task**:
   1. Write the tests first.
   2. Implement.
   3. Get `make check` green.
   4. For UI tasks, check the running app in the browser with Claude in Chrome.
   5. Run a code-review subagent, fix the findings, and re-review.
   6. Get the user's review.
   7. Make **one commit**.
3. **Commits follow Conventional Commits** (`feat:`, `fix:`, `test:`, `refactor:`, `chore:`, `docs:`, `ci:`), with
   **one commit per task**. Never commit before the user has reviewed the task.
4. **Specs, plans and brainstorm files** live in `docs/superpowers/` and `.superpowers/`. They are local only and
   gitignored. **Never commit them.**
5. **Don't skip verification.** Report results honestly: say so when a check fails or a step was skipped.
