"""MCP server exposing a read-only slice of the Genesys Cloud Platform API.

Run for interactive testing (opens the MCP Inspector web UI):
    mcp dev server.py

Install into Claude Desktop:
    mcp install server.py --name "Genesys Cloud"

Or wire into Claude Code / another MCP client manually — see README.md.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from config import Settings
from genesys_client import GenesysClient

settings = Settings.from_env()
client = GenesysClient(settings.client_id, settings.client_secret, settings.environment)

mcp = FastMCP("genesys-cloud")


@mcp.tool()
def list_queues(name_filter: str = "") -> list[dict]:
    """List Genesys Cloud routing queues, optionally filtered by a case-insensitive
    substring of the queue name. Returns each queue's id and name — use the id
    with get_queue_aggregates or search_conversations."""
    params = {"pageSize": 100}
    if name_filter:
        params["name"] = name_filter
    data = client.request("GET", "/api/v2/routing/queues", params=params)
    return [{"id": q["id"], "name": q["name"]} for q in data.get("entities", [])]


@mcp.tool()
def get_queue_aggregates(queue_id: str, start: str, end: str) -> dict:
    """Get aggregate KPIs for one queue over a time window: offered/answered/
    abandoned counts, handle/talk/ACW time, and service level.

    queue_id: id from list_queues.
    start, end: ISO-8601 UTC timestamps, e.g. '2026-08-12T00:00:00.000Z'.
    """
    body = {
        "interval": f"{start}/{end}",
        "granularity": "PT30M",
        "groupBy": ["queueId"],
        "filter": {
            "type": "and",
            "predicates": [{"dimension": "queueId", "value": queue_id}],
        },
        "metrics": [
            "nOffered",
            "nAnswered",
            "nAbandon",
            "tAbandon",
            "tAnswered",
            "tHandle",
            "tTalk",
            "tAcw",
            "oServiceLevel",
        ],
    }
    return client.request("POST", "/api/v2/analytics/queues/aggregates/query", json=body)


@mcp.tool()
def search_conversations(queue_id: str, start: str, end: str, limit: int = 25) -> dict:
    """Search conversations that touched a queue within a time window — useful
    for pulling concrete examples when drilling into an anomaly.

    queue_id: id from list_queues.
    start, end: ISO-8601 UTC timestamps, e.g. '2026-08-12T00:00:00.000Z'.
    limit: max conversations to return (default 25).
    """
    body = {
        "interval": f"{start}/{end}",
        "order": "desc",
        "orderBy": "conversationStart",
        "paging": {"pageSize": limit, "pageNumber": 1},
        "segmentFilters": [
            {"type": "and", "predicates": [{"dimension": "queueId", "value": queue_id}]}
        ],
    }
    return client.request("POST", "/api/v2/analytics/conversations/details/query", json=body)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
