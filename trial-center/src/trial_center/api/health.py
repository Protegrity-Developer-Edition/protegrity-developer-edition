"""Health check endpoints."""

from __future__ import annotations

import logging
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)


def check_health() -> dict[str, Any]:
    """Check health of all services.

    Returns:
        Health status dictionary with service statuses
    """
    return {
        "status": "healthy",
        "version": "1.2.0",
        "services": {
            "guardrail": check_guardrail_service(),
            "discovery": check_discovery_service(),
        }
    }


def check_guardrail_service() -> dict[str, Any]:
    """Check if semantic guardrail service is reachable.

    Returns:
        Service health status
    """
    try:
        response = requests.get(
            "http://localhost:8581/health",
            timeout=5
        )
        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "latency_ms": int(response.elapsed.total_seconds() * 1000)
        }
    except Exception as e:
        LOGGER.error(f"Guardrail health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


def check_discovery_service() -> dict[str, Any]:
    """Check if discovery service is reachable.

    Returns:
        Service health status
    """
    try:
        response = requests.get(
            "http://localhost:8580/health",
            timeout=5
        )
        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "latency_ms": int(response.elapsed.total_seconds() * 1000)
        }
    except Exception as e:
        LOGGER.error(f"Discovery health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
