"""
Protegrity Developer Edition session helper.
Manages authentication and keeps the session alive with automatic refresh.
"""

import os
import time
import threading
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Module-level session state ────────────────────────────────────
_lock = threading.Lock()
_session_token = None
_session_expiry = 0
_http_session = requests.Session()
_dev_edition_available = None  # None = not checked yet, True/False after first attempt

# Config from .env
DEV_EDITION_EMAIL = os.getenv("DEV_EDITION_EMAIL")
DEV_EDITION_PASSWORD = os.getenv("DEV_EDITION_PASSWORD")
DEV_EDITION_API_KEY = os.getenv("DEV_EDITION_API_KEY")
PROTEGRITY_HOST = os.getenv("PROTEGRITY_HOST", "http://localhost:8580")
PROTEGRITY_API_TIMEOUT = int(os.getenv("PROTEGRITY_API_TIMEOUT", "30"))

# Re-auth 5 minutes before expiry (assuming 30-min session lifetime)
SESSION_LIFETIME_SECONDS = 25 * 60
MAX_RETRIES = 3
RETRY_DELAY = 2


def _authenticate():
    """Authenticate with Protegrity Developer Edition and store the session token."""
    global _session_token, _session_expiry, _dev_edition_available

    auth_url = f"{PROTEGRITY_HOST}/pty/dev-edition/v1/sessions"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": DEV_EDITION_API_KEY,
    }
    payload = {
        "email": DEV_EDITION_EMAIL,
        "password": DEV_EDITION_PASSWORD,
    }

    logger.info("Authenticating with Protegrity Developer Edition...")
    try:
        resp = _http_session.post(
            auth_url, json=payload, headers=headers, timeout=PROTEGRITY_API_TIMEOUT
        )
        # Check if Dev Edition endpoint exists
        if resp.status_code == 404:
            logger.info("Dev Edition session endpoint not found (404). Running without authentication.")
            _dev_edition_available = False
            _session_token = None
            _session_expiry = 0
            return None
        resp.raise_for_status()
        data = resp.json()

        # Extract token — adapt field name to actual API response
        _session_token = (
            data.get("sessionToken")
            or data.get("token")
            or data.get("access_token")
            or data.get("ptytoken")
        )
        _session_expiry = time.time() + SESSION_LIFETIME_SECONDS

        logger.info("Protegrity Developer Edition session authenticated successfully.")
        _dev_edition_available = True
        return _session_token
    except requests.RequestException as e:
        logger.error(f"Protegrity authentication failed: {e}")
        _session_token = None
        _session_expiry = 0
        _dev_edition_available = False
        logger.warning("Dev Edition auth failed: %s. Continuing without authentication.", e)
        return None


def get_session_credentials():
    """
    Return valid session credentials (token + headers).
    Automatically re-authenticates if the session is expired or missing.
    """
    global _session_token, _session_expiry

    with _lock:
        if _session_token is None or time.time() >= _session_expiry:
            logger.info("Session expired or missing — re-authenticating...")
            _authenticate()

    headers = {
        "Content-Type": "application/json",
        "x-api-key": DEV_EDITION_API_KEY,
    }
    if _session_token:
        headers["Authorization"] = f"Bearer {_session_token}"

    return _session_token, headers


def invalidate_session():
    """Force the next call to re-authenticate (e.g., after a 401)."""
    global _session_token, _session_expiry
    with _lock:
        _session_token = None
        _session_expiry = 0
        logger.info("Protegrity session invalidated — will re-auth on next call.")


def protegrity_request(method, url, retries=MAX_RETRIES, **kwargs):
    """
    Make an HTTP request to a Protegrity endpoint with automatic
    session refresh and retry on 401/connection errors.
    """
    kwargs.setdefault("timeout", PROTEGRITY_API_TIMEOUT)
    last_exception = None

    # If Dev Edition is known to be unavailable, make direct unauthenticated requests
    with _lock:
        dev_available = _dev_edition_available
    if dev_available is False:
        resp = _http_session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp

    for attempt in range(1, retries + 1):
        _, headers = get_session_credentials()
        # Merge caller headers with session headers
        req_headers = headers.copy()
        if "headers" in kwargs:
            req_headers.update(kwargs.pop("headers"))

        try:
            resp = _http_session.request(
                method, url, headers=req_headers, **kwargs
            )

            if resp.status_code == 401:
                logger.warning(
                    f"401 Unauthorized on attempt {attempt}/{retries} to {url} — "
                    f"invalidating session and retrying."
                )
                invalidate_session()
                if attempt < retries:
                    time.sleep(RETRY_DELAY * attempt)
                    continue
                resp.raise_for_status()

            resp.raise_for_status()
            return resp

        except requests.RequestException as e:
            last_exception = e
            logger.warning(
                f"Request to {url} failed (attempt {attempt}/{retries}): {e}"
            )
            invalidate_session()
            if attempt < retries:
                time.sleep(RETRY_DELAY * attempt)

    raise last_exception


def close_session():
    """Clean up the HTTP session."""
    _http_session.close()
    logger.info("Protegrity HTTP session closed.")