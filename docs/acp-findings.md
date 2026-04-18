# Phase 0.5 — goosed API Findings

Verified against goosed v1.30.0 (Goose Desktop, Fedora). Tested 2026-04-18.

---

## Protocol

goosed runs **HTTPS** with a **self-signed certificate** (`CN=goosed localhost`).
All clients must use `-k` / `verify=False` / `ssl._create_unverified_context()`.

Plain HTTP returns `Received HTTP/0.9` — not a valid response. Always use HTTPS.

---

## Port

goosed picks a **dynamic port** each time Goose Desktop starts. There is no fixed port.

**How to find it at runtime:**

```bash
ss -tlnp | grep goosed
# or
cat /proc/$(pgrep goosed)/environ | tr '\0' '\n' | grep GOOSE_SERVER__SECRET_KEY
```

The port is embedded in `/proc/<pid>/environ` alongside the secret (see below).

---

## Authentication

All routes except `/status` require the header:

```
X-Secret-Key: <secret>
```

- `Authorization: Bearer` returns 401 — **wrong scheme**.
- The secret is set via the `GOOSE_SERVER__SECRET_KEY` environment variable when goosed starts.
- Goose Desktop generates a fresh random secret each launch and injects it into the goosed process.
- **How to read it:** `cat /proc/$(pgrep goosed)/environ | tr '\0' '\n' | grep GOOSE_SERVER__SECRET_KEY`

The gateway must read port + secret from `/proc/<pid>/environ` on startup.

---

## Endpoints

### `GET /status` — health check (no auth)
```
200 OK
body: "ok"
```

### `GET /sessions` — list sessions
```json
{
  "sessions": [{ "id": "20260418_3", "name": "...", "working_dir": "...", ... }]
}
```

### `POST /agent/start` — create a new session
Request body:
```json
{ "working_dir": "/home/theron" }
```
Returns the full session object. Key field: `"id"` (e.g. `"20260418_5"`).

**Important:** New sessions have `provider_name: null`. Calling `/reply` on them returns `{"type":"Error","error":"Provider not set"}`. Must call `/agent/update_provider` immediately after creation.

### `POST /agent/update_provider` — configure provider for a session
Must be called after `/agent/start` before the session can reply.
```json
{ "session_id": "20260418_5", "provider": "mistral", "model": "mistral-medium" }
```
Returns 200 on success.

### `POST /reply` — send a message to a session (SSE stream)
Request body:
```json
{
  "session_id": "20260418_5",
  "user_message": {
    "role": "user",
    "created": 1776531600,
    "metadata": { "userVisible": true, "agentVisible": true },
    "content": [{ "type": "text", "text": "your message here" }]
  }
}
```

Response: `text/event-stream` (SSE). Event types:
- `{"type":"Ping"}` — keepalive, emitted every ~1s while thinking
- `{"type":"Message","message":{...},"token_state":{...}}` — assistant reply chunk
- `{"type":"Finish","reason":"stop","token_state":{...}}` — stream end
- `{"type":"Error","error":"..."}` — e.g. `"Provider not set"`

**Streaming chunks:** With Mistral, a single assistant turn arrives as multiple `Message` events sharing the same `"id"`, each carrying a text chunk. To reconstruct the full reply: group by `message.id`, concatenate the `content[].text` values across events in arrival order.

The `message` field in a Message event:
```json
{
  "id": "ec60b4c5...",
  "role": "assistant",
  "created": 1776531739,
  "content": [{ "type": "text", "text": "chunk" }],
  "metadata": { "userVisible": true, "agentVisible": true }
}
```

### `GET /config` — current goosed config
Returns extensions, provider, daemon IPC config, etc.

---

## Gateway Design Implications

1. **Port discovery:** Read `GOOSE_SERVER__SECRET_KEY` and the port from `/proc/$(pgrep goosed)/environ` at startup. No config file needed.
2. **One session per Signal thread:** Create via `POST /agent/start`, store `session_id` keyed by Signal sender.
3. **Reply loop:** `POST /reply` → stream SSE → collect all `Message` events → concatenate text → send back to Signal.
4. **No MCP protocol needed.** goosed exposes its own REST/SSE API. The `goosed mcp` subcommand is separate and not needed here.
5. **TLS:** Always `verify=False` — self-signed cert, no CA to trust.
