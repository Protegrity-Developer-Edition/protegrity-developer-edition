"""
FastAPI backend — Protegrity Secure Data Bridge.

Platform connectivity (GitHub, Gmail, Slack, Google Sheets) is managed by
Composio. COMPOSIO_API_KEY is the only platform credential this service holds;
there are deliberately no endpoints for supplying per-platform tokens.
"""
from __future__ import annotations
import logging, os, sys
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from config import load_config
from agent import ProtegrityConnectedAgent, RBAC_ROLES, LIVE_APPS
import composio_bridge as cc
import google_drive as gd
import pipeline as pl
import gmail_client as gmc
import email_pipeline as ep
import slack_pipeline as sp
import mock_demo_pipeline as mdp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Protegrity Secure Data Bridge", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_frontend = Path(__file__).parent / "frontend" / "index.html"
_static = Path(__file__).parent / "frontend" / "static"
if _static.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")


# ── request models ────────────────────────────────────────────────────────────

class DemoRunRequest(BaseModel):
    repo: str
    rbac_role: str = "admin"
    spreadsheet_title: Optional[str] = None
    write_to_sheets: bool = True

class TestRepoRequest(BaseModel):
    repo: str

class GmailRunRequest(BaseModel):
    default_repo: str = ""
    dry_run: bool = False

class AskRequest(BaseModel):
    prompt: str
    mode: str = "auto"          # "auto" | "live" | "demo"

class RevealRequest(BaseModel):
    text: str
    role: str = "viewer"

class SlackRecipient(BaseModel):
    identifier: str             # Slack email, @username, or display name
    role: str = "viewer"        # "admin" (unprotected) | "viewer" (protected)
    display_name: Optional[str] = None

class SlackRunRequest(BaseModel):
    repo: str
    recipients: list[SlackRecipient]
    dry_run: bool = False
    preview_mode: bool = False
    use_sgr: bool = True

class MockDemoRequest(BaseModel):
    run_guardrails: bool = True


# ── app shell ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    if _frontend.exists():
        return HTMLResponse(content=_frontend.read_text())
    return HTMLResponse("<h1>Frontend not found</h1>", 404)


@app.get("/api/health")
async def health():
    import requests as rlib
    cfg = load_config()
    s: Dict[str, Any] = {
        "status": "ok",
        "protegrity": {"classify": False, "sgr": False},
        "composio": cc.status(),
        "openai": {"configured": bool(cfg.openai_api_key)},
    }
    try:
        r = rlib.post(cfg.classify_url, json={"text": "test"}, timeout=3)
        s["protegrity"]["classify"] = r.status_code < 500
    except Exception as e:
        s["protegrity"]["classify_error"] = str(e)
    try:
        r = rlib.post(cfg.sgr_url,
                      json={"messages": [{"from": "user", "to": "ai", "content": "hello",
                                          "processors": []}]},
                      timeout=3)
        s["protegrity"]["sgr"] = r.status_code < 500
    except Exception as e:
        s["protegrity"]["sgr_error"] = str(e)
    return s


@app.get("/api/roles")
async def get_roles():
    return {"roles": [{"id": k, **v} for k, v in RBAC_ROLES.items()]}


# ── Composio connections ──────────────────────────────────────────────────────

@app.get("/api/connected-apps")
async def connected_apps():
    """Live connection state straight from Composio. The UI is read-only over this."""
    status = cc.status()
    toolkits = status.get("toolkits") or []
    connected = [t for t in toolkits if t["connected"]]
    return {
        "toolkits": toolkits,
        "connected_accounts": status.get("apps") or [],
        "agent_apps": LIVE_APPS,
        "composio": {k: v for k, v in status.items() if k not in ("apps", "toolkits")},
        "connect_url": "https://dashboard.composio.dev",
        "mode": "live" if connected else "demo",
    }


# ── Connected Agent ───────────────────────────────────────────────────────────

@app.post("/api/ask")
async def ask(req: AskRequest):
    if not req.prompt or len(req.prompt.strip()) < 3:
        raise HTTPException(400, "Prompt too short.")
    cfg = load_config()
    try:
        return ProtegrityConnectedAgent(cfg=cfg).run(req.prompt.strip(), mode=req.mode)
    except Exception as e:
        logger.exception("Agent run failed")
        raise HTTPException(500, str(e))


@app.post("/api/reveal")
async def reveal(req: RevealRequest):
    if not req.text:
        raise HTTPException(400, "No text supplied.")
    cfg = load_config()
    return ProtegrityConnectedAgent(cfg=cfg).reveal(req.text, req.role)


# ── GitHub → Protegrity → Google Sheets ───────────────────────────────────────

@app.post("/api/demo/test-repo")
async def test_repo(req: TestRepoRequest):
    """Confirm the repo is reachable through the Composio GitHub connection."""
    if not req.repo or "/" not in req.repo:
        raise HTTPException(400, "repo must be owner/repo")
    try:
        issues = pl.fetch_github_issues(req.repo, limit=1)
        return {"ok": True, "repo": req.repo, "reachable_issues": len(issues),
                "source": "composio"}
    except cc.ComposioError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/demo/run")
async def demo_run(req: DemoRunRequest):
    if not req.repo or "/" not in req.repo:
        raise HTTPException(400, "repo must be owner/repo")
    cfg = load_config()
    try:
        result = pl.run_full_pipeline(repo=req.repo, cfg=cfg, rbac_role=req.rbac_role)
    except cc.ComposioError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Pipeline error")
        raise HTTPException(500, f"Pipeline error: {e}")

    sheets_result = None
    if req.write_to_sheets:
        try:
            title = req.spreadsheet_title or \
                f"GitHub Issues — {req.repo.split('/')[-1]} — Protegrity Demo"
            sheets_result = gd.create_issues_spreadsheet(
                result["stage_3_unprotect"]["issues"], title=title)
            sheets_result["ok"] = True
        except Exception as e:
            logger.exception("Sheets write failed")
            sheets_result = {"ok": False, "error": str(e)}
    result["stage_4_sheets"] = sheets_result
    return result


# ── Gmail ─────────────────────────────────────────────────────────────────────

@app.get("/api/gmail/status")
async def gmail_status():
    connected = gmc.is_connected()
    return {"connected": connected,
            "email": gmc.get_connected_email() if connected else None,
            "source": "composio"}


@app.post("/api/gmail/test")
async def gmail_test():
    if not gmc.is_connected():
        return {"ok": False, "error": "Gmail is not connected in Composio."}
    return gmc.GmailClient().test_connection()


@app.post("/api/gmail/preview")
async def gmail_preview(req: GmailRunRequest):
    """Dry-run: fetch emails + parse intent, but DO NOT send any replies."""
    return _run_gmail(req, dry_run=True)


@app.post("/api/gmail/run")
async def gmail_run(req: GmailRunRequest):
    """Read unread emails → parse intent → GitHub → Protegrity → send replies."""
    return _run_gmail(req, dry_run=False)


def _run_gmail(req: GmailRunRequest, dry_run: bool):
    if not gmc.is_connected():
        raise HTTPException(400, "Gmail is not connected in Composio.")
    cfg = load_config()
    try:
        return ep.run_email_pipeline(
            gmail_client=gmc.GmailClient(), cfg=cfg,
            default_repo=req.default_repo, dry_run=dry_run,
        )
    except cc.ComposioError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Gmail pipeline failed")
        raise HTTPException(500, str(e))


# ── Slack ─────────────────────────────────────────────────────────────────────

@app.post("/api/slack/test")
async def slack_test():
    """Verify the Slack toolkit is reachable through Composio."""
    return sp.test_slack_connection()


@app.post("/api/slack/run")
async def slack_run(req: SlackRunRequest):
    """
    1. Fetch today's top-5 GitHub issues (via Composio)
    2. Protegrity Gate 1 (find_and_protect) — tokenise PII
    3. Semantic Guardrail scan on protected payload
    4. Preview mode: per-role previews. Real mode: Gate 2 for admins, send DMs
    """
    if not req.repo or "/" not in req.repo:
        raise HTTPException(400, "repo must be owner/repo")
    cfg = load_config()
    try:
        return sp.run_slack_pipeline(
            repo=req.repo,
            recipients=[r.model_dump() for r in req.recipients],
            cfg=cfg,
            dry_run=req.dry_run,
            preview_mode=req.preview_mode,
            use_sgr=req.use_sgr,
        )
    except cc.ComposioError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Slack pipeline failed")
        raise HTTPException(500, str(e))


# ── Mock demo ─────────────────────────────────────────────────────────────────

@app.post("/api/mock/run")
async def mock_run(req: MockDemoRequest):
    """
    Fully-mocked walkthrough:
      Inbound Email → GitHub Issues → Protegrity Gate 1 (protect)
      → Semantic Guardrails → Outbound Email → Spreadsheet

    Real Protegrity APIs are called; platform data is mock.
    """
    cfg = load_config()
    try:
        return mdp.run_mock_pipeline(cfg=cfg, run_guardrails=req.run_guardrails)
    except Exception as e:
        logger.exception("Mock pipeline failed")
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8900))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
