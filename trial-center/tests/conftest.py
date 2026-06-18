"""Shared test configuration and fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path for test imports
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(autouse=True)
def mock_credentials(monkeypatch):
    """Provide fake credentials so tests never need real ones."""
    monkeypatch.setenv("DEV_EDITION_EMAIL", "test@example.com")
    monkeypatch.setenv("DEV_EDITION_PASSWORD", "fake-password")
    monkeypatch.setenv("DEV_EDITION_API_KEY", "fake-api-key-0000")


@pytest.fixture
def sample_prompt():
    """Return a typical user prompt for testing."""
    return "My name is John Smith and my email is john@example.com"


@pytest.fixture
def fixtures_dir():
    """Return path to the test fixtures directory."""
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def sample_approved(fixtures_dir):
    """Load the sample approved prompt fixture."""
    return (fixtures_dir / "sample_approved.txt").read_text().strip()


@pytest.fixture
def sample_malicious(fixtures_dir):
    """Load the sample malicious prompt fixture."""
    return (fixtures_dir / "sample_malicious.txt").read_text().strip()
