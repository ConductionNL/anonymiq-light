"""CORS is off unless a deployment names its browser origins.

ALLOWED_ORIGINS used to default to "*", so every web page could read every
response. The settings are read once, when ``src.api.config`` is imported, so
each case starts the app in a fresh interpreter with its own environment and
drives it through TestClient. No server, no lifespan, no spaCy model.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ALLOWED = "https://allowed.example"
OTHER = "https://evil.example"

PROBE = """
import json
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
simple = client.get("/api/v1/health", headers={"Origin": ORIGIN})
preflight = client.options(
    "/api/v1/analyze",
    headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"},
)
print(json.dumps({
    "simple": simple.headers.get("access-control-allow-origin"),
    "preflight": preflight.headers.get("access-control-allow-origin"),
    "middleware": [m.cls.__name__ for m in app.user_middleware],
}))
"""


def probe(tmp_path: Path, origin: str, allowed_origins: str | None) -> dict:
    """Start the app with the given ALLOWED_ORIGINS and send one request."""
    env = {k: v for k, v in os.environ.items() if k != "ALLOWED_ORIGINS"}
    env["LOG_DIR"] = str(tmp_path / "logs")
    if allowed_origins is not None:
        env["ALLOWED_ORIGINS"] = allowed_origins
    result = subprocess.run(
        [sys.executable, "-c", f"ORIGIN = {origin!r}\n{PROBE}"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("allowed_origins", [None, ""], ids=["unset", "empty"])
def test_no_configured_origin_keeps_cors_off(
    tmp_path: Path, allowed_origins: str | None
) -> None:
    """Unset or empty: no allow header, not even for a preflight."""
    seen = probe(tmp_path, OTHER, allowed_origins)
    assert seen["simple"] is None
    assert seen["preflight"] is None
    assert "CORSMiddleware" not in seen["middleware"]


def test_a_configured_origin_is_allowed(tmp_path: Path) -> None:
    """The origin named in ALLOWED_ORIGINS is echoed back, not a wildcard."""
    seen = probe(tmp_path, ALLOWED, f"{ALLOWED}/, https://other.example")
    assert seen["simple"] == ALLOWED
    assert seen["preflight"] == ALLOWED


def test_a_non_configured_origin_gets_no_allow_header(tmp_path: Path) -> None:
    """An origin that is not listed gets nothing back."""
    seen = probe(tmp_path, OTHER, ALLOWED)
    assert seen["simple"] is None
    assert seen["preflight"] is None


def test_parse_allowed_origins_has_no_wildcard_by_default() -> None:
    """Unset or empty means no origin at all; entries are trimmed."""
    from src.api.config import parse_allowed_origins

    assert parse_allowed_origins(None) == []
    assert parse_allowed_origins("") == []
    assert parse_allowed_origins(" https://a.example , https://b.example/ ,") == [
        "https://a.example",
        "https://b.example",
    ]
