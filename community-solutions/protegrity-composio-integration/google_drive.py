"""
Google Sheets / Drive output for the Protegrity demo.

All access goes through the Composio GOOGLESHEETS toolkit — this project stores
no Google OAuth client, token or service account of its own.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List

import composio_bridge as cc

logger = logging.getLogger(__name__)

TOOLKIT = "GOOGLESHEETS"

# Slugs and argument names verified against the live Composio catalogue.
SHEETS_TOOLS = {
    "create": ["GOOGLESHEETS_CREATE_GOOGLE_SHEET1", "GOOGLESHEETS_CREATE_SPREADSHEET"],
    "write": ["GOOGLESHEETS_VALUES_UPDATE", "GOOGLESHEETS_UPDATE_VALUES_BATCH"],
}


def _a1_range(rows: List[List[str]]) -> str:
    """A1 range wide enough for the header row, e.g. 8 columns -> Sheet1!A1:H<n>."""
    width = max((len(r) for r in rows), default=1)
    last_col = ""
    n = width
    while n > 0:
        n, rem = divmod(n - 1, 26)
        last_col = chr(65 + rem) + last_col
    return f"Sheet1!A1:{last_col}{len(rows)}"


def _dig(payload: Any, *keys: str) -> Any:
    """Return the first present key from a possibly-nested Composio response."""
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if key in payload:
            return payload[key]
    for nested in ("data", "response_data", "details", "spreadsheet"):
        found = _dig(payload.get(nested), *keys)
        if found is not None:
            return found
    return None


def is_connected() -> bool:
    return cc.is_app_connected(TOOLKIT)


def _issue_rows(issues: List[Dict[str, Any]]) -> List[List[str]]:
    rows = [["#", "Title", "Author", "State", "Created", "Labels", "URL", "Body Preview"]]
    for issue in issues:
        user = issue.get("user", {})
        login = user.get("login", "") if isinstance(user, dict) else str(user)
        labels = issue.get("labels") or []
        label_str = ", ".join(
            (lb.get("name", "") if isinstance(lb, dict) else str(lb)) for lb in labels
        )
        rows.append([
            str(issue.get("number", "")),
            issue.get("title", ""),
            login,
            issue.get("state", ""),
            (issue.get("created_at", "") or "")[:10],
            label_str,
            issue.get("html_url", ""),
            (issue.get("body") or "")[:300].replace("\n", " "),
        ])
    return rows


def create_issues_spreadsheet(
    issues: List[Dict[str, Any]],
    title: str = "GitHub Issues — Protegrity Demo",
) -> Dict[str, Any]:
    """
    Create a Google Spreadsheet with GitHub issue data via Composio.
    Returns {"spreadsheet_id": ..., "url": ..., "rows_written": ...}
    """
    cc.require_app(TOOLKIT)

    created = cc.execute_first(SHEETS_TOOLS["create"], {"title": title})
    sid = _dig(created, "spreadsheetId", "spreadsheet_id", "id")
    if not sid:
        raise cc.ComposioError(f"Composio did not return a spreadsheet id for '{title}'")

    rows = _issue_rows(issues)
    cc.execute_first(SHEETS_TOOLS["write"], {
        "spreadsheet_id": sid,
        "range": _a1_range(rows),
        "value_input_option": "RAW",
        "values": rows,
    })

    url = _dig(created, "spreadsheetUrl", "spreadsheet_url", "url") \
        or f"https://docs.google.com/spreadsheets/d/{sid}"
    logger.info("Created spreadsheet %s via Composio (%d rows)", sid, len(rows) - 1)
    return {
        "spreadsheet_id": sid,
        "url": url,
        "rows_written": len(rows) - 1,
        "title": title,
        "source": "composio",
    }
