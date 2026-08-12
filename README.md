# Genesys Cloud MCP Server (read-only)

A minimal MCP server wrapping three read-only Genesys Cloud Platform API calls, meant as the
foundation described in [`../Genesys-RCA-Agent-Architecture.md`](../Genesys-RCA-Agent-Architecture.md).
Grow this by adding more `@mcp.tool()` functions in `server.py` as the RCA agent needs more
signal (agent adherence, IVR flow errors, edge/telephony health, quality evaluations, ...).

Tools included:
- `list_queues(name_filter)` — resolve a queue name to its id.
- `get_queue_aggregates(queue_id, start, end)` — SLA%, ASA, abandon %, AHT etc. for a window.
- `search_conversations(queue_id, start, end, limit)` — conversation-level detail for a window.

> **Not tested against a live org.** The request bodies for the two analytics endpoints follow
> Genesys Cloud's documented query shape, but Genesys's exact field/metric names have shifted
> across API versions before. Before wiring this into anything scheduled, run each tool once
> through the MCP Inspector (step 4) against your real org and fix up any field names that come
> back wrong — the error message from `GenesysApiError` will include Genesys's own response body,
> which usually says exactly what's missing/misnamed.

## 1. Create a read-only OAuth client in Genesys Cloud

1. Admin → Integrations → OAuth → **Add Client**.
2. Grant type: **Client Credentials**.
3. Roles: assign (or create) a custom role with only **view**-level permissions — at minimum:
   `routing:queue:view`, and the relevant `analytics:*:view` permissions for queue observations,
   queue aggregates, and conversation details. Do **not** grant any write/edit permissions —
   this server has no business needing them, and it removes an entire class of risk if the
   client secret ever leaks.
4. Save, then copy the **Client ID** and **Client Secret** — the secret is only shown once.
5. Note your org's region domain (Admin → Organization Settings, or look at the domain you log
   in through) — e.g. `mypurecloud.com`, `usw2.pure.cloud`, `mypurecloud.ie`.

## 2. Local setup

Requires **Python 3.10+**. (Not currently installed on this machine — grab it from
[python.org](https://www.python.org/downloads/) or `winget install Python.Python.3.12` if you're
setting this up here; a real deployment would run this on a server/container instead anyway.)

```bash
cd genesys-mcp-server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with the client id/secret/environment from step 1.

## 3. Sanity-check the Genesys auth call

Before involving MCP at all, confirm the OAuth client works:

```bash
python -c "from config import Settings; from genesys_client import GenesysClient; s=Settings.from_env(); c=GenesysClient(s.client_id, s.client_secret, s.environment); print(c.request('GET', '/api/v2/routing/queues', params={'pageSize': 1}))"
```

If that prints queue JSON, auth and network access are good. If it raises `GenesysAuthError`,
double check the client id/secret/environment. If it raises a 403 on the queues call, the
OAuth client's role is missing `routing:queue:view`.

## 4. Test the MCP server interactively (no Claude needed yet)

The `mcp[cli]` package ships an Inspector — a local web UI that lets you call each tool by hand
and see the raw response, without wiring up a real MCP client first:

```bash
mcp dev server.py
```

This prints a local URL — open it, and you should see `list_queues`, `get_queue_aggregates`, and
`search_conversations` listed as tools. Run `list_queues` first to get a real `queue_id`, then
try `get_queue_aggregates` with a recent time window and see whether the response shape matches
what the tool's docstring promises. Fix up `server.py` here before moving on.

## 5. Connect it to Claude

**Claude Desktop** — one command registers it:

```bash
mcp install server.py --name "Genesys Cloud"
```

This writes an entry into Claude Desktop's `claude_desktop_config.json` pointing at this
server's venv Python and `server.py`, and picks up your `.env` automatically. Restart Claude
Desktop and the three tools should show up under the 🔌 icon.

**Claude Code** (this CLI) — add it as a project or user MCP server:

```bash
claude mcp add genesys-cloud -- python "C:\Users\g352280\OneDrive - Principal Financial Group\Ai\Claude\genesys-mcp-server\server.py"
```

(Run that from a real terminal, not this session — Claude Code reads MCP config at startup.)
Or add it by hand to `.mcp.json` / `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "genesys-cloud": {
      "command": "python",
      "args": ["C:\\Users\\g352280\\OneDrive - Principal Financial Group\\Ai\\Claude\\genesys-mcp-server\\server.py"]
    }
  }
}
```

## 6. Next steps

- Add the remaining tools from the architecture doc's catalog (agent adherence, IVR flow
  execution, edge/telephony health, quality evaluations) the same way — one `@mcp.tool()`
  function per Genesys endpoint, in `server.py`.
- Move `.env` secrets to a real vault (Azure Key Vault) before this runs anywhere but your
  laptop.
- Once there's more than a couple of tools, consider splitting `server.py` into one module per
  Genesys API area (analytics, routing, telephony, quality) and importing them into a single
  `FastMCP` instance.
