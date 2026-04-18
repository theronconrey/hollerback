# goose-signal-gateway

A Python service that bridges Signal Messenger to [Goose Desktop](https://github.com/block/goose) via the `goosed` REST API. Signal conversations become live Goose sessions — you can message your AI from your phone and see the same session in Goose Desktop.

**Status:** Proof of concept. Core loop works. Not production-hardened.

---

## How it works

```
Signal (phone) → signal-cli daemon → gateway → goosed → Mistral/OpenAI/etc → Signal reply
```

- Subscribes to the `signal-cli` HTTP daemon's SSE event stream
- Routes each sender to a dedicated `goosed` session
- Streams the Goose reply back as a Signal message
- Sessions are visible in Goose Desktop alongside any you start manually

## Requirements

- Linux (uses `/proc` for goosed discovery — not portable to macOS/Windows)
- [Goose Desktop](https://github.com/block/goose) installed and running
- [signal-cli](https://github.com/AsamK/signal-cli) 0.13+ running in HTTP daemon mode on `127.0.0.1:8080`
- Python 3.12+
- [uv](https://github.com/astral-sh/uv)

## Setup

```bash
git clone https://github.com/theronconrey/goose-signal-gateway
cd goose-signal-gateway
uv sync
```

Run signal-cli in daemon mode (if not already):
```bash
signal-cli --config ~/.local/share/signal-cli daemon --http 127.0.0.1:8080
```

Start the gateway:
```bash
uv run main.py --account +1XXXXXXXXXX
```

Where `--account` is the Signal phone number linked to your signal-cli installation.

## Configuration

The gateway auto-discovers `goosed` at startup by scanning `/proc` for the process and reading its port and auth secret from the process environment. No config file needed.

Provider and model default to `mistral` / `mistral-medium` — whatever is configured in your Goose Desktop installation. To change:

```python
# In gateway.py _handle(), pass provider/model to create_session():
session_id = await self._goosed.create_session(provider="openai", model="gpt-4o")
```

Configurable CLI flags will come in a later version.

## Known limitations

- **No message dedup** — duplicate Signal deliveries will trigger duplicate Goose replies
- **Sessions not persisted** — restarting the gateway loses sender→session mappings (new sessions created on next message)
- **No reconnect on goosed restart** — if Goose Desktop restarts, the gateway must be restarted too
- **Linux only** — goosed discovery reads `/proc`; macOS/Windows not supported
- **One session per sender** — no concept of threads or topics within a conversation

## Architecture

```
src/goose_signal_gateway/
├── gateway.py         # main loop: SSE subscribe → route → reply
├── goosed_client.py   # goosed REST/SSE client + process discovery
├── signal_client.py   # signal-cli HTTP client (send + SSE subscribe)
└── session_store.py   # in-memory sender → session_id map
```

See `docs/acp-findings.md` for the full goosed API contract discovered during development.

## License

MIT
