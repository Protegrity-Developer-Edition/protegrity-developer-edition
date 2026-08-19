"""
Single access layer for Composio, over Composio Connect's MCP endpoint.

Auth is the `ck_...` consumer key sent as `x-consumer-api-key`. That key is only
valid for MCP — the REST API expects a separate platform key.

This project is the MCP *client*: tool results land in this process, so the
Protegrity gates still wrap every payload before an LLM sees it. That property
would be lost if the LLM framework talked to the MCP server directly.

Composio Connect exposes seven meta-tools rather than app tools. App tools are
reached through COMPOSIO_MULTI_EXECUTE_TOOL by slug.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

DEFAULT_MCP_URL = "https://connect.composio.dev/mcp"
DEFAULT_USER_ID = os.environ.get("COMPOSIO_USER_ID", "default")
CALL_TIMEOUT = 180

# Values that look configured but are not.
_PLACEHOLDER_KEYS = {
    "", "your_api_key_here", "your-api-key-here", "changeme",
    "ck_...", "pak_xxx", "none", "null",
}

# Composio Connect cannot enumerate connections; toolkits must be named explicitly.
# All of these are probed in a single call (~2s for 20).
KNOWN_TOOLKITS = [
    "github", "gmail", "slack", "googlesheets", "googledrive", "googledocs",
    "googlecalendar", "notion", "linear", "jira", "hubspot", "salesforce",
    "asana", "trello", "dropbox", "airtable", "discord", "outlook",
    "zoom", "confluence",
]

# Display names for toolkits we surface in the UI.
TOOLKIT_NAMES = {
    "GITHUB": "GitHub", "GMAIL": "Gmail", "SLACK": "Slack",
    "GOOGLESHEETS": "Google Sheets", "GOOGLEDRIVE": "Google Drive",
    "GOOGLEDOCS": "Google Docs", "GOOGLECALENDAR": "Google Calendar",
    "NOTION": "Notion", "LINEAR": "Linear", "JIRA": "Jira",
    "HUBSPOT": "HubSpot", "SALESFORCE": "Salesforce", "ASANA": "Asana",
    "TRELLO": "Trello", "DROPBOX": "Dropbox", "AIRTABLE": "Airtable",
    "DISCORD": "Discord", "OUTLOOK": "Outlook", "ZOOM": "Zoom",
    "CONFLUENCE": "Confluence",
}

_lock = threading.Lock()
_loop: Optional[asyncio.AbstractEventLoop] = None
_tool_cache: Dict[str, str] = {}


class ComposioError(RuntimeError):
    """A Composio call could not be completed."""


# ── configuration ─────────────────────────────────────────────────────────────

def api_key() -> str:
    return (os.environ.get("COMPOSIO_API_KEY") or "").strip()


def mcp_url() -> str:
    return (os.environ.get("COMPOSIO_MCP_URL") or DEFAULT_MCP_URL).strip()


def is_configured() -> bool:
    key = api_key()
    return bool(key) and key.lower() not in _PLACEHOLDER_KEYS


def _require_config() -> None:
    if not is_configured():
        raise ComposioError(
            "COMPOSIO_API_KEY is missing or still a placeholder. Set the Composio "
            "consumer key (ck_...) in .env — it is the only platform credential this app uses."
        )


# ── async plumbing ────────────────────────────────────────────────────────────
# Pipelines are sync and FastAPI handlers are async, so coroutines run on a
# dedicated background loop rather than the request loop.

def _background_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
            threading.Thread(target=_loop.run_forever, daemon=True,
                             name="composio-mcp").start()
        return _loop


def _run(coro) -> Any:
    return asyncio.run_coroutine_threadsafe(coro, _background_loop()).result(CALL_TIMEOUT)


async def _call_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Open an MCP session, call one meta-tool, return its text payload."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {"x-consumer-api-key": api_key()}
    async with streamablehttp_client(mcp_url(), headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            return "\n".join(getattr(c, "text", "") or "" for c in result.content)


async def _list_mcp_tools() -> List[Dict[str, Any]]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {"x-consumer-api-key": api_key()}
    async with streamablehttp_client(mcp_url(), headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            return [
                {"name": t.name, "description": t.description or t.name,
                 "schema": t.inputSchema or {"type": "object", "properties": {}}}
                for t in listing.tools
            ]


def _flatten(exc: BaseException) -> str:
    """anyio wraps failures in ExceptionGroups, which hide the real cause."""
    if isinstance(exc, BaseExceptionGroup):
        return "; ".join(_flatten(e) for e in exc.exceptions)
    return f"{type(exc).__name__}: {exc}"


def _meta_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    _require_config()
    try:
        raw = _run(_call_tool(name, arguments))
    except ComposioError:
        raise
    except Exception as exc:
        raise ComposioError(f"Composio MCP call {name} failed: {_flatten(exc)}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"data": raw, "error": None, "successful": True}


# ── connected accounts ────────────────────────────────────────────────────────

def toolkit_states(toolkits: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    """
    Connection state for every probed toolkit.

    Composio reports "initiated" for any toolkit that was never connected, so a
    toolkit counts as connected only when it actually has an account.
    """
    slugs = [t.lower() for t in (toolkits or KNOWN_TOOLKITS)]
    payload = _meta_call("COMPOSIO_MANAGE_CONNECTIONS", {
        "toolkits": [{"name": s, "action": "list"} for s in slugs]
    })
    if payload.get("error"):
        raise ComposioError(f"Could not list connections: {payload['error']}")

    results = ((payload.get("data") or {}).get("results")) or {}
    states: List[Dict[str, Any]] = []
    for slug in slugs:
        info = results.get(slug) or {}
        accounts = info.get("accounts") or []
        app = slug.upper()
        states.append({
            "slug": app,
            "name": TOOLKIT_NAMES.get(app, slug.title()),
            "connected": bool(accounts),
            "status": (info.get("status") or "unknown").upper(),
            "accounts": [
                {
                    "id": a.get("id", ""),
                    "status": (a.get("status") or "").upper(),
                    "identity": (a.get("user_info") or {}).get("email")
                                or (a.get("user_info") or {}).get("login") or "",
                    "is_default": bool(a.get("is_default")),
                }
                for a in accounts
            ],
        })
    return states


def connected_apps(toolkits: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    """Flat list of real connected accounts."""
    accounts: List[Dict[str, Any]] = []
    for state in toolkit_states(toolkits):
        for acct in state["accounts"]:
            accounts.append({
                "id": acct["id"],
                "app": state["slug"],
                "name": state["name"],
                "status": acct["status"] or "ACTIVE",
                "identity": acct["identity"],
                "user_id": DEFAULT_USER_ID,
                "disabled": False,
            })
    return accounts


def active_app_slugs() -> set[str]:
    return {s["slug"] for s in toolkit_states() if s["connected"]}


def is_app_connected(slug: str) -> bool:
    try:
        return slug.upper() in active_app_slugs()
    except ComposioError:
        return False


def account_for(slug: str) -> Dict[str, Any]:
    """The active connected account for a toolkit, or a user-actionable error."""
    slug = slug.upper()
    accounts = connected_apps()
    for a in accounts:
        if a["app"] == slug:
            return a
    have = ", ".join(sorted({a["app"] for a in accounts})) or "none"
    raise ComposioError(
        f"No Composio connection for {slug}. Connected toolkits: {have}. "
        f"Connect it at dashboard.composio.dev, then retry."
    )


def require_app(slug: str) -> None:
    account_for(slug)


# ── tool execution ────────────────────────────────────────────────────────────

def search_tools(use_case: str) -> List[str]:
    """Tool slugs Composio suggests for a use case."""
    payload = _meta_call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": use_case}]})
    return sorted(set(re.findall(r"\b[A-Z][A-Z0-9]+_[A-Z0-9_]{3,}\b", json.dumps(payload))))


def resolve_tool(candidates: Sequence[str]) -> str:
    """
    Return the first candidate slug Composio recognises.

    Tool naming drifts between releases, so callers pass known aliases rather
    than betting on one hardcoded slug.
    """
    if not candidates:
        raise ComposioError("resolve_tool() requires at least one candidate slug")
    cache_key = "|".join(candidates)
    if cache_key in _tool_cache:
        return _tool_cache[cache_key]

    payload = _meta_call("COMPOSIO_GET_TOOL_SCHEMAS", {"tool_slugs": list(candidates)})
    body = json.dumps(payload)
    for slug in candidates:
        # A schema response echoes the slug it resolved; unknown slugs are omitted.
        if f'"{slug}"' in body:
            _tool_cache[cache_key] = slug
            return slug

    # Fall back to trusting the first candidate; execute() will report a bad slug.
    _tool_cache[cache_key] = candidates[0]
    return candidates[0]


def _unwrap(payload: Dict[str, Any], tool: str) -> Any:
    """Pull the app payload out of the MULTI_EXECUTE envelope."""
    if payload.get("error"):
        raise ComposioError(f"Composio tool {tool} failed: {payload['error']}")

    results = ((payload.get("data") or {}).get("results")) or []
    if not results:
        raise ComposioError(f"Composio returned no result for {tool}")

    response = (results[0] or {}).get("response") or {}
    if not response.get("successful", True):
        raise ComposioError(f"Composio tool {tool} failed: {response.get('error') or response}")
    return response.get("data", response)


def execute(
    tool: str,
    arguments: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    account: Optional[str] = None,
) -> Any:
    """Execute one app tool through Composio and return its data payload."""
    logger.info("Composio execute: %s", tool)
    spec: Dict[str, Any] = {"tool_slug": tool, "arguments": arguments or {}}
    if account:
        spec["account"] = account
    payload = _meta_call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [spec]})
    return _unwrap(payload, tool)


def execute_first(
    candidates: Sequence[str],
    arguments: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Any:
    return execute(resolve_tool(candidates), arguments, user_id)


def call_meta(name: str, arguments: Dict[str, Any]) -> Any:
    """Invoke a Composio meta-tool directly — used by the agent's tool loop."""
    return _meta_call(name, arguments)


def get_openai_tools(apps: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    """
    OpenAI function-tool definitions for the Composio meta-tools.

    Connect exposes meta-tools, not app tools: the agent searches for what it
    needs and executes by slug. `apps` is accepted for call-site compatibility.
    """
    _require_config()
    try:
        tools = _run(_list_mcp_tools())
    except Exception as exc:
        raise ComposioError(f"Could not load Composio MCP tools: {exc}") from exc
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": (t["description"] or t["name"])[:1024],
                "parameters": t["schema"],
            },
        }
        for t in tools
    ]


def resolve_transport(app: str, requested: str = "auto") -> str:
    """Deprecated: every platform call now goes through Composio."""
    require_app(app)
    return "composio"


# ── diagnostics ───────────────────────────────────────────────────────────────

def status() -> Dict[str, Any]:
    """Honest health payload — never hides a misconfiguration."""
    info: Dict[str, Any] = {
        "configured": is_configured(),
        "transport": "mcp",
        "url": mcp_url(),
        "reachable": False,
        "connected_apps": 0,
        "toolkits": [],
        "apps": [],
        "error": None,
    }
    try:
        import mcp  # noqa: F401
    except ImportError as exc:
        info["error"] = f"mcp client library not installed: {exc}"
        return info

    if not info["configured"]:
        info["error"] = (
            "COMPOSIO_API_KEY is missing or a placeholder — Composio calls are disabled."
        )
        return info

    try:
        states = toolkit_states()
    except ComposioError as exc:
        info["error"] = str(exc)
        return info

    info["reachable"] = True
    info["toolkits"] = states
    info["apps"] = [a for s in states for a in s["accounts"]]
    info["connected_apps"] = len([s for s in states if s["connected"]])
    return info
