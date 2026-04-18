# goose-signal-gateway

Read `~/Projects/standards.md` before any work on this project.

## What this is

A Python service that bridges Signal Messenger to a running `goosed` via the Agent Client Protocol (ACP). Signal conversations become first-class Goose sessions, visible in both Signal and Goose Desktop.

This is a standalone validation prototype — not an in-tree Goose contribution.

## Implementation plan

Full phased spec: `docs/PLAN.md`. Read the entire plan before writing any code.

**Critical:** Phase 0.5 (verify ACP contract against a live goosed) must happen before Phase 5. Do not skip it.

## Environment

- Fedora. Use `dnf`, never `apt`.
- Python 3.12+ managed with `uv`.
- Goose Desktop is installed (provides goosed). Must be running for ACP testing.
- `signal-cli` running at `127.0.0.1:8080` — already linked to the account on this machine.
- Mistral API configured in Goose.

## Code location

`~/Projects/Personal/goose-signal-gateway/` — canonical.
Git remote: to be created at `github.com/theronconrey/goose-signal-gateway`.

## Context

This project is part of a planned migration away from OpenClaw on borealis.home. OpenClaw currently handles the Signal channel, cron jobs, and daily briefings. Once this gateway is stable, those responsibilities move to Goose + this service.

Migration is sequenced after METRC eval completion — do not deprecate OpenClaw until this is running and tested.
