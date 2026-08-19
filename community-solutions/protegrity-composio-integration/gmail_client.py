"""
Gmail access for the Protegrity demo.

All access goes through the Composio GMAIL toolkit — this project stores no
Google OAuth client, refresh token or app password of its own.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import composio_bridge as cc

logger = logging.getLogger(__name__)

TOOLKIT = "GMAIL"

# Composio renames these tools between releases; try the known aliases.
GMAIL_TOOLS = {
    "profile": ["GMAIL_GET_PROFILE", "GMAIL_FETCH_PROFILE", "GMAIL_GET_CONTACTS"],
    "fetch": ["GMAIL_FETCH_EMAILS", "GMAIL_LIST_MESSAGES", "GMAIL_LIST_EMAILS"],
    "reply": ["GMAIL_REPLY_TO_THREAD", "GMAIL_SEND_EMAIL", "GMAIL_CREATE_EMAIL_DRAFT"],
    "mark_read": ["GMAIL_MODIFY_THREAD_LABELS", "GMAIL_MODIFY_MESSAGE_LABELS",
                  "GMAIL_REMOVE_LABEL"],
}


def _dig(payload: Any, *keys: str) -> Any:
    """Return the first present key from a possibly-nested Composio response."""
    if not isinstance(payload, dict):
        return None
    for key in keys:
        if key in payload:
            return payload[key]
    for nested in ("data", "response_data", "details"):
        found = _dig(payload.get(nested), *keys)
        if found is not None:
            return found
    return None


def is_connected() -> bool:
    return cc.is_app_connected(TOOLKIT)


def get_connected_email() -> Optional[str]:
    """Gmail address of the Composio-connected account, or None."""
    try:
        return GmailClient().test_connection().get("email") or None
    except Exception:
        return None


class GmailClient:
    """Reads and replies to mail through the Composio GMAIL toolkit."""

    def __init__(self, user_id: Optional[str] = None):
        cc.require_app(TOOLKIT)
        self._user_id = user_id or cc.DEFAULT_USER_ID

    def _call(self, key: str, params: Dict[str, Any]) -> Any:
        return cc.execute_first(GMAIL_TOOLS[key], params, user_id=self._user_id)

    def test_connection(self) -> Dict[str, Any]:
        try:
            data = self._call("profile", {"user_id": "me"})
            return {"ok": True, "email": _dig(data, "emailAddress", "email") or "",
                    "source": "composio"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def fetch_unread_recent(self, hours: int = 24) -> List[Dict[str, Any]]:
        since_ts = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
        data = self._call("fetch", {
            "user_id": "me",
            "query": f"is:unread after:{since_ts}",
            "max_results": 20,
        })
        messages = _dig(data, "messages", "emails", "items") or []
        results: List[Dict[str, Any]] = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            hdrs = {k.lower(): v for k, v in (msg.get("headers") or {}).items()}
            results.append({
                "imap_id": msg.get("messageId") or msg.get("id", ""),
                "msg_id": hdrs.get("message-id", ""),
                "thread_id": msg.get("threadId") or msg.get("thread_id", ""),
                "from": msg.get("sender") or hdrs.get("from", ""),
                "subject": msg.get("subject") or hdrs.get("subject", "(no subject)"),
                "body": (msg.get("messageText") or msg.get("body") or "")[:2000],
                "date": msg.get("messageTimestamp") or hdrs.get("date", ""),
            })
        logger.info("Fetched %d unread messages via Composio", len(results))
        return results

    def send_reply(self, original: Dict[str, Any], body_text: str) -> None:
        subj = original.get("subject", "")
        self._call("reply", {
            "user_id": "me",
            "thread_id": original.get("thread_id", ""),
            "recipient_email": original["from"],
            "subject": subj if subj.lower().startswith("re:") else f"Re: {subj}",
            "message_body": body_text,
            "body": body_text,
            "is_html": False,
        })
        logger.info("Reply sent to %s via Composio", original["from"])

    def mark_as_read(self, imap_id: str) -> None:
        self._call("mark_read", {
            "user_id": "me",
            "message_id": imap_id,
            "thread_id": imap_id,
            "remove_label_ids": ["UNREAD"],
        })
