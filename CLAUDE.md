# goose-signal-gateway

## What this is

A Python service bridging Signal Messenger to Goose Desktop via the `goosed` REST/SSE API. Signal conversations become live Goose sessions.

This is a proof-of-concept prototype. Not an in-tree Goose contribution.

## Key findings (read before modifying)

Full API contract: `docs/acp-findings.md`. Critical points:

- goosed runs **HTTPS** with a self-signed cert. Always `verify=False`.
- Auth header is `X-Secret-Key`, not `Authorization: Bearer`.
- Port is dynamic per Goose Desktop launch. Discovered via `/proc` at startup.
- New sessions need `POST /agent/update_provider` before they can reply.
- signal-cli in daemon mode: use SSE at `GET /api/v1/events`. The `receive` JSON-RPC method does not work in daemon mode.

## Environment

- Linux (uses `/proc` for goosed discovery)
- Python 3.12+ managed with `uv`
- Goose Desktop must be running
- signal-cli running as HTTP daemon at `127.0.0.1:8080`

## Running

```bash
uv sync
uv run main.py --account +1XXXXXXXXXX
```
