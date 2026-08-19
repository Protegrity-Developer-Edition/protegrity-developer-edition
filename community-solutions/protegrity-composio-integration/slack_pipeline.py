"""
GitHub → Protegrity → Slack pipeline.

Flow:
  1.  Fetch the top 5 GitHub issues created/updated today
  2.  Protegrity Gate 1: find_and_protect  (tokenise all PII)
  3.  For each configured recipient:
        • RBAC role == "admin"  → Gate 2: find_and_unprotect  → send plain text
        • RBAC role == "viewer" → skip Gate 2              → send tokenised text
  4.  Deliver a formatted Slack DM to each recipient

Recipient is identified by Slack @username, display name, real name, or email.
GitHub and Slack are both reached through Composio — this project stores no
platform tokens of its own.
"""
from __future__ import annotations

import json, logging, re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import Config, load_config
import protegrity_bridge as pb
import composio_bridge as cc
from pipeline import fetch_github_issues, _slim_issue

logger = logging.getLogger(__name__)

# Composio renames Slack tools between releases; try the known aliases.
SLACK_TOOLS = {
    "auth_test": ["SLACK_TEST_AUTH", "SLACK_AUTH_TEST", "SLACK_CHECKS_API_CALLING_CODE"],
    "find_by_email": ["SLACK_FIND_USER_BY_EMAIL_ADDRESS", "SLACK_FIND_USERS_BY_EMAIL_ADDRESS",
                      "SLACK_LOOKUP_USER_BY_EMAIL"],
    "list_users": ["SLACK_LIST_ALL_USERS", "SLACK_LIST_ALL_SLACK_TEAM_USERS_WITH_PAGINATION",
                   "SLACK_FETCH_ALL_SLACK_TEAM_USERS_WITH_PAGINATION"],
    "open_dm": ["SLACK_OPEN_DM", "SLACK_INITIATES_OR_RESUMES_A_DIRECT_MESSAGE_OR_MULTI_PERSON_DIRECT_MESSAGE",
                "SLACK_OPENS_OR_RESUMES_A_DIRECT_MESSAGE_OR_MULTI_PERSON_DIRECT_MESSAGE"],
    "post_message": ["SLACK_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL", "SLACK_CHAT_POST_MESSAGE",
                     "SLACK_SEND_MESSAGE"],
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

# ── issue helpers ─────────────────────────────────────────────────────────────

def fetch_today_issues(repo: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch up to `limit` issues created OR updated in the last 24 h.
    Falls back to the most-recent `limit` issues if none are from today.
    """
    issues = fetch_github_issues(repo, limit=20, state="open", sort="updated")

    # Try to return issues updated within the last 24 h
    today = [
        i for i in issues
        if _hours_ago(i.get("updated_at") or i.get("created_at", "")) <= 24
    ]
    chosen = today[:limit] if today else issues[:limit]
    return [_slim_issue(i) for i in chosen]


def _hours_ago(iso: str) -> float:
    """Return how many hours ago an ISO-8601 timestamp was. Returns inf on error."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        return delta.total_seconds() / 3600
    except Exception:
        return float("inf")


# ── Slack client (via Composio) ───────────────────────────────────────────────

class SlackClient:
    """Talks to Slack through the Composio SLACK toolkit, which holds the auth."""

    def __init__(self, user_id: Optional[str] = None):
        cc.require_app("SLACK")
        self._user_id = user_id or cc.DEFAULT_USER_ID

    def _call(self, key: str, params: Dict[str, Any]) -> Any:
        return cc.execute_first(SLACK_TOOLS[key], params, user_id=self._user_id)

    def auth_test(self) -> str:
        data = self._call("auth_test", {})
        return _dig(data, "user", "user_name", "bot_name") or "ProtegrityBot"

    def resolve_user_id(self, identifier: str) -> Optional[str]:
        identifier = identifier.strip().lstrip("@")
        if "@" in identifier and "." in identifier.split("@")[-1]:
            try:
                data = self._call("find_by_email", {"email": identifier})
                user = _dig(data, "user") or {}
                user_id = user.get("id") if isinstance(user, dict) else None
                if user_id:
                    return user_id
            except cc.ComposioError as e:
                logger.info("Slack email lookup failed for %s: %s", identifier, e)

        cursor = None
        while True:
            params: Dict[str, Any] = {"limit": 200}
            if cursor:
                params["cursor"] = cursor
            try:
                data = self._call("list_users", params)
            except cc.ComposioError as e:
                logger.warning("Slack list_users failed: %s", e)
                return None
            members = _dig(data, "members") or []
            for member in members:
                if member.get("deleted") or member.get("is_bot"):
                    continue
                profile = member.get("profile", {}) or {}
                if (member.get("name", "").lower() == identifier.lower()
                        or profile.get("display_name", "").lower() == identifier.lower()
                        or profile.get("real_name", "").lower() == identifier.lower()):
                    return member.get("id")
            cursor = ((_dig(data, "response_metadata") or {}) or {}).get("next_cursor")
            if not cursor:
                return None

    def open_dm(self, user_id: str) -> str:
        data = self._call("open_dm", {"users": user_id})
        channel = _dig(data, "channel") or {}
        channel_id = channel.get("id") if isinstance(channel, dict) else channel
        if not channel_id:
            raise cc.ComposioError(f"Composio did not return a DM channel for user {user_id}")
        return channel_id

    def post_message(self, channel: str, text: str, blocks: List[Dict]) -> None:
        self._call("post_message", {
            "channel": channel,
            "text": text,
            "blocks": json.dumps(blocks),
        })


def _build_blocks(
    issues: List[Dict],
    repo: str,
    is_protected: bool,
    sender_note: str = "",
) -> List[Dict]:
    """Build Slack Block Kit message blocks."""
    status_emoji = "🔒" if is_protected else "🔓"
    status_label = "PII tokenised (protected)" if is_protected else "PII de-tokenised (plain text)"
    header_text = (
        f"{status_emoji} *Top GitHub issues from `{repo}`*\n"
        f"_{status_label}_"
    )
    blocks: List[Dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": f"GitHub Issues — {repo}", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": header_text}},
        {"type": "divider"},
    ]

    for iss in issues:
        user = iss.get("user") or {}
        login = user.get("login", "unknown") if isinstance(user, dict) else str(user)
        labels = ", ".join(iss.get("labels") or []) or "none"
        preview = (iss.get("body") or "")[:200].replace("\n", " ").strip()
        state_emoji = "🟢" if iss.get("state") == "open" else "⚫"
        issue_text = (
            f"*#{iss.get('number')} — {iss.get('title', '')}*\n"
            f"{state_emoji} {iss.get('state', '')}  •  👤 {login}  •  🏷 {labels}\n"
            f"📅 {(iss.get('created_at') or '')[:10]}"
        )
        if preview:
            issue_text += f"\n> {preview[:180]}"
        url = iss.get("html_url", "")
        block: Dict[str, Any] = {
            "type": "section",
            "text": {"type": "mrkdwn", "text": issue_text},
        }
        if url:
            block["accessory"] = {
                "type": "button",
                "text": {"type": "plain_text", "text": "Open →", "emoji": True},
                "url": url,
                "action_id": f"issue_{iss.get('number')}",
            }
        blocks.append(block)
        blocks.append({"type": "divider"})

    footer = f"_Delivered by Protegrity × Composio Secure Data Bridge_"
    if sender_note:
        footer = f"_{sender_note}_\n{footer}"
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": footer}})
    return blocks


# ── Mock GitHub issues — used when preview_mode=True ─────────────────────────
MOCK_GITHUB_ISSUES = [
    {
        "number": 2341, "state": "open",
        "title": "Payment failure for customer John Smith — card ending 1234",
        "user": {"login": "alice.johnson", "email": "alice.johnson@acme.com"},
        "body": ("Customer John Smith (john.smith@acme.com, +1-650-555-0147) reported payment failure. "
                 "SSN on file: 123-45-6789. CC: 4532-0151-1283-0366 expires 09/28."),
        "labels": ["bug", "payments"],
        "created_at": "2026-05-15T09:00:00Z", "updated_at": "2026-05-15T09:30:00Z",
        "html_url": "https://github.com/demo/secure-app/issues/2341",
    },
    {
        "number": 2342, "state": "open",
        "title": "Update PII fields for user profile — DOB mismatch",
        "user": {"login": "bob.wilson", "email": "bob.wilson@acme.com"},
        "body": ("Alice Johnson (DOB: 1985-07-22, IP: 192.168.1.100) has a DOB mismatch. "
                 "Contact: alice.j@personal.com or +1 (415) 555-2671."),
        "labels": ["data-quality"],
        "created_at": "2026-05-15T10:00:00Z", "updated_at": "2026-05-15T10:15:00Z",
        "html_url": "https://github.com/demo/secure-app/issues/2342",
    },
    {
        "number": 2343, "state": "open",
        "title": "SSN validation failing in onboarding flow",
        "user": {"login": "carol.white", "email": "carol.white@acme.com"},
        "body": ("Onboarding for David Clark (SSN: 321-54-9876, "
                 "Address: 123 Market St, San Francisco, CA 94105) returns error 422. "
                 "Bank account: 4012-8888-8888-1881."),
        "labels": ["onboarding", "validation"],
        "created_at": "2026-05-15T08:30:00Z", "updated_at": "2026-05-15T09:00:00Z",
        "html_url": "https://github.com/demo/secure-app/issues/2343",
    },
    {
        "number": 2344, "state": "open",
        "title": "Email notification sent to wrong address",
        "user": {"login": "dave.martin"},
        "body": ("Password reset for frank.harris@example.com was sent to frank.harris@gmail.com. "
                 "Customer DOB 1978-11-30, phone +1 (212) 555-0147."),
        "labels": ["email", "privacy"],
        "created_at": "2026-05-14T16:00:00Z", "updated_at": "2026-05-15T07:00:00Z",
        "html_url": "https://github.com/demo/secure-app/issues/2344",
    },
    {
        "number": 2345, "state": "open",
        "title": "GDPR export request — grace.martinez@business.org",
        "user": {"login": "security-bot"},
        "body": ("GDPR export for Grace Martinez (grace.m@business.org, +1 (312) 555-9876, "
                 "456 Oak Ave, Chicago, IL 60601). Request ID: GDPR-2026-0512."),
        "labels": ["gdpr", "compliance"],
        "created_at": "2026-05-12T11:00:00Z", "updated_at": "2026-05-15T06:00:00Z",
        "html_url": "https://github.com/demo/secure-app/issues/2345",
    },
]

# ── main pipeline ─────────────────────────────────────────────────────────────

def run_slack_pipeline(
    repo: str,
    recipients: List[Dict[str, str]],   # [{"identifier": "...", "role": "admin|viewer"}, ...]
    cfg: Optional[Config] = None,
    dry_run: bool = False,
    preview_mode: bool = False,
    use_sgr: bool = True,
) -> Dict[str, Any]:
    """
    Run the full GitHub → Protegrity → Slack pipeline. Both platforms are
    reached through Composio.

    preview_mode=True  — use MOCK_GITHUB_ISSUES (no GitHub call), force dry_run
    preview_mode=False — fetch real issues; send real Slack DMs when dry_run=False
    """
    if cfg is None:
        cfg = load_config()

    if preview_mode:
        dry_run = True  # preview always implies dry-run

    can_send = cc.is_app_connected("SLACK")

    # ── Stage 1: Fetch (or load mock) issues ────────────────────────────────
    if preview_mode:
        issues = MOCK_GITHUB_ISSUES
        repo = repo or "demo/secure-app"
    else:
        issues = fetch_today_issues(repo, limit=5)
        if not issues:
            return {
                "ok": False,
                "error": f"No issues found in {repo}",
                "issues_found": 0,
            }

    # ── Stage 2: Protegrity Gate 1 — protect each field individually ──────────
    # Treating the whole JSON blob as text causes numeric fields (issue numbers,
    # dates) to be mis-tagged and corrupted.  Protecting text fields one-by-one
    # gives the classifier proper context and preserves the JSON structure.
    def _protect_issue_fields(issue: dict) -> tuple:
        """Return a PII-protected copy of the issue + all elements detected."""
        p = dict(issue)
        elems: list = []
        for field in ("title", "body"):
            val = issue.get(field) or ""
            if val:
                r = pb.find_and_protect(val, cfg=cfg)
                p[field] = r.protected
                elems.extend(r.elements_found)
        user = issue.get("user") or {}
        if isinstance(user, dict):
            p_user = dict(user)
            for uf in ("login", "email"):
                if user.get(uf):
                    r = pb.find_and_protect(user[uf], cfg=cfg)
                    p_user[uf] = r.protected
                    elems.extend(r.elements_found)
            p["user"] = p_user
        return p, elems

    protected_issues: list = []
    all_elements: list = []
    for issue in issues:
        p_issue, elems = _protect_issue_fields(issue)
        protected_issues.append(p_issue)
        all_elements.extend(elems)

    protected_json = json.dumps(protected_issues, indent=2)
    pii_count = len(all_elements)

    # Cache the unprotected version (Gate 2) for admin recipients
    _unprotected: Dict[str, Any] = {}  # lazy: computed once if any admin exists

    def _get_unprotected() -> List[Dict]:
        nonlocal _unprotected
        if not _unprotected:
            r = pb.find_and_unprotect(protected_json, cfg=cfg)
            try:
                _unprotected["issues"] = json.loads(r.protected)
            except Exception:
                _unprotected["issues"] = issues  # fallback to raw
        return _unprotected["issues"]

    # ── Stage 3: Semantic Guardrail scan on protected payload ─────────────────
    if use_sgr:
        sgr = pb.semantic_guardrail_check(protected_json, cfg=cfg)
    else:
        sgr = {"accepted": True, "risk_score": 0.0, "outcome": "skipped", "raw": {}}
    # In real (non-dry-run) mode, hard-block if SGR flags the payload.
    # In dry-run / preview mode, record the result but continue so the demo
    # can show all pipeline steps even when guardrail flags content.
    if use_sgr and not sgr["accepted"] and not dry_run and can_send:
        return {
            "ok": False,
            "sgr_blocked": True,
            "sgr": sgr,
            "repo": repo,
            "issues_found": len(issues),
            "pii_count": pii_count,
            "issues": issues,
            "protected_json": protected_json,
            "recipients": [],
            "sent_count": 0,
            "dry_run": dry_run,
            "error": f"Semantic Guardrail blocked the payload — risk score {sgr['risk_score']:.2%}",
        }

    # ── Stage 4: Preview mode (dry_run, or Slack not connected) ──────────────
    # Build per-recipient previews without touching the Slack API.
    # Pre-compute unprotected issues for admin previews.
    if dry_run or not can_send:
        results = []
        for rec in recipients:
            role = rec.get("role", "viewer")
            identifier = rec.get("identifier", "").strip()
            display_name = rec.get("display_name") or identifier or "Preview"
            if role == "admin":
                preview_issues = _get_unprotected()
                is_protected = False
            else:
                try:
                    preview_issues = json.loads(protected_json)
                except Exception:
                    preview_issues = issues
                is_protected = True
            results.append({
                "identifier": identifier,
                "display_name": display_name,
                "role": role,
                "user_id": None,
                "sent": False,
                "protected": is_protected,
                "error": None,
                "preview_issues": preview_issues,
            })
        return {
            "ok": True,
            "repo": repo,
            "issues_found": len(issues),
            "pii_count": pii_count,
            "issues": issues,
            "protected_json": protected_json,
            "sgr": sgr,
            "dry_run": True,
            "recipients": results,
            "sent_count": 0,
            "source": "composio",
        }

    # ── Stage 5: Actual Slack delivery ───────────────────────────────────
    try:
        client = SlackClient()
        bot_name = client.auth_test()
    except cc.ComposioError as e:
        return {"ok": False, "error": f"Slack unavailable via Composio: {e}",
                "issues_found": len(issues), "sgr": sgr, "source": "composio"}

    results = []
    for rec in recipients:
        identifier = rec.get("identifier", "").strip()
        role = rec.get("role", "viewer")
        display_name = rec.get("display_name") or identifier

        rec_result: Dict[str, Any] = {
            "identifier": identifier,
            "display_name": display_name,
            "role": role,
            "user_id": None,
            "sent": False,
            "protected": role != "admin",
            "error": None,
        }

        if not identifier:
            rec_result["error"] = "Empty identifier — skipped"
            results.append(rec_result)
            continue

        # Resolve Slack user
        user_id = client.resolve_user_id(identifier)
        if not user_id:
            rec_result["error"] = f"Could not find Slack user '{identifier}'"
            results.append(rec_result)
            continue
        rec_result["user_id"] = user_id

        # Choose PII visibility based on role
        if role == "admin":
            send_issues = _get_unprotected()
            is_protected = False
            sender_note = f"Sent to {display_name} as admin — PII de-tokenised"
        else:
            try:
                send_issues = json.loads(protected_json)
            except Exception:
                send_issues = issues
            is_protected = True
            sender_note = f"Sent to {display_name} as viewer — PII remains tokenised"

        blocks = _build_blocks(send_issues, repo, is_protected, sender_note)
        try:
            channel_id = client.open_dm(user_id)
            client.post_message(
                channel=channel_id,
                text=f"Top GitHub issues from {repo} ({('🔓 plain' if role == 'admin' else '🔒 protected')})",
                blocks=blocks,
            )
            rec_result["sent"] = True
        except cc.ComposioError as e:
            rec_result["error"] = str(e)

        results.append(rec_result)

    return {
        "ok": True,
        "repo": repo,
        "issues_found": len(issues),
        "pii_count": pii_count,
        "issues": issues,
        "protected_json": protected_json,
        "sgr": sgr,
        "dry_run": False,
        "recipients": results,
        "sent_count": sum(1 for r in results if r["sent"]),
        "source": "composio",
    }


def test_slack_connection() -> Dict[str, Any]:
    """Verify the Slack toolkit is reachable through Composio."""
    try:
        bot_user = SlackClient().auth_test()
        return {"ok": True, "bot_user": bot_user, "source": "composio"}
    except cc.ComposioError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
