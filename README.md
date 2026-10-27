# YouScan Dashboard

A full-stack dashboard (React + FastAPI + Postgres) with chart widgets imported from spreadsheet files.

Status: in development

## Prerequisites

- Docker with Compose v2.1+
- [uv](https://docs.astral.sh/uv/)
- pre-commit (installed by `make install`)
- Node 24 (see `.nvmrc`) and pnpm, needed from the frontend onward

## Quick start

```sh
make install && make dev-db
```

Postgres runs on `localhost:54329` (user/password `dashboard`).
