"""
Real end-to-end pipeline:
  GitHub Issues → Protegrity Gate 1 (Protect) → Protegrity Gate 2 (Unprotect) → Google Sheets

All platform access goes through Composio — this project holds no GitHub credentials.
Each stage is recorded so the UI can show raw / protected / unprotected side-by-side.
"""
from __future__ import annotations
import json, logging, re, sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from config import Config, load_config
import protegrity_bridge as pb
import composio_bridge as cc

logger = logging.getLogger(__name__)

# Composio has renamed this tool across releases; try the known aliases.
GITHUB_LIST_ISSUES_TOOLS = [
    "GITHUB_LIST_REPOSITORY_ISSUES",
    "GITHUB_ISSUES_LIST_FOR_REPO",
    "GITHUB_LIST_ISSUES",
]

GITHUB_GET_ISSUE_TOOLS = [
    "GITHUB_GET_AN_ISSUE",
    "GITHUB_ISSUES_GET",
    "GITHUB_GET_ISSUE",
]


def _coerce_issue_list(data: Any) -> List[Dict[str, Any]]:
    """Composio wraps GitHub payloads inconsistently; unwrap to a list of issues."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("details", "data", "items", "issues", "response_data"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    raise cc.ComposioError(f"Unexpected GitHub payload from Composio: {type(data).__name__}")


# ── GitHub (via Composio) ─────────────────────────────────────────────────────

def fetch_github_issues(
    repo: str,
    limit: int = 5,
    state: str = "all",
    sort: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch the last `limit` issues from a repository through the Composio GITHUB
    toolkit. repo format: "owner/repo-name"
    """
    if "/" not in repo:
        raise ValueError(f"repo must be 'owner/repo', got: {repo!r}")
    cc.require_app("GITHUB")
    owner, name = repo.split("/", 1)
    params: Dict[str, Any] = {"owner": owner, "repo": name, "state": state, "per_page": limit}
    if sort:
        params["sort"] = sort
        params["direction"] = "desc"
    data = cc.execute_first(GITHUB_LIST_ISSUES_TOOLS, params)
    # GitHub returns PRs on the issues endpoint — filter them out.
    issues = [i for i in _coerce_issue_list(data) if "pull_request" not in i]
    return issues[:limit]


def _slim_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only the fields we need to display and protect."""
    user = issue.get("user") or {}
    labels = issue.get("labels") or []
    return {
        "number": issue.get("number"),
        "title":  issue.get("title", ""),
        "state":  issue.get("state", ""),
        "user":   {"login": user.get("login", ""), "email": user.get("email", "")},
        "created_at": (issue.get("created_at") or "")[:10],
        "html_url": issue.get("html_url", ""),
        "labels": [lb.get("name", "") if isinstance(lb, dict) else str(lb) for lb in labels],
        "body": (issue.get("body") or "")[:500],
    }


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_full_pipeline(
    repo: str,
    cfg: Optional[Config] = None,
    rbac_role: str = "admin",
) -> Dict[str, Any]:
    """
    Execute the full demo pipeline and return all stages.

    Returns:
        {
            "stage_1_fetch":       { issues: [...], json: "..." },
            "stage_2_protect":     { protected_json: "...", elements: [...] },
            "stage_3_unprotect":   { unprotected_json: "...", issues: [...] },
            "pii_count":           int,
            "repo":                str,
            "error":               None | str,
        }
    """
    cfg = cfg or load_config()

    # ── Stage 1: Fetch ────────────────────────────────────────────────────────
    logger.info("Stage 1: Fetching GitHub issues from %s via Composio", repo)
    raw_issues = fetch_github_issues(repo, limit=5)
    slimmed = [_slim_issue(i) for i in raw_issues]
    raw_json = json.dumps(slimmed, indent=2)
    logger.info("Fetched %d issues", len(slimmed))

    # ── Stage 2: Protegrity Gate 1 — Protect (tokenize PII) ──────────────────
    logger.info("Stage 2: Protegrity find_and_protect")
    protect_result = pb.find_and_protect(raw_json, cfg=cfg)
    protected_json = protect_result.protected
    elements = protect_result.elements_found
    logger.info("Gate 1 complete: %d PII elements found", len(elements))

    # ── Stage 3: Protegrity Gate 2 — Unprotect (detokenize for Drive output) ──
    can_reveal = rbac_role.lower() == "admin"
    if can_reveal:
        logger.info("Stage 3: Protegrity find_and_unprotect (role=%s)", rbac_role)
        unprotect_result = pb.find_and_unprotect(protected_json, cfg=cfg)
        unprotected_json = unprotect_result.protected
    else:
        logger.info("Stage 3: Redacted (role=%s has no reveal permission)", rbac_role)
        unprotect_result = pb.find_and_redact(protected_json, cfg=cfg)
        unprotected_json = unprotect_result.protected

    # Parse unprotected JSON back to list (best effort)
    try:
        unprotected_issues = json.loads(unprotected_json)
    except Exception:
        unprotected_issues = slimmed  # fallback to raw if parse fails
        logger.warning("Could not parse unprotected JSON; using raw issues for Drive write")

    return {
        "stage_1_fetch": {
            "issues": slimmed,
            "json": raw_json,
            "count": len(slimmed),
            "source": "composio",
        },
        "stage_2_protect": {
            "protected_json": protected_json,
            "elements": elements,
            "pii_detected": protect_result.pii_detected,
        },
        "stage_3_unprotect": {
            "unprotected_json": unprotected_json,
            "issues": unprotected_issues,
            "rbac_role": rbac_role,
            "revealed": can_reveal,
        },
        "pii_count": len(elements),
        "repo": repo,
        "error": None,
    }
