"""The importable Postman requests must match the actual HTTP application."""

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from match_intelligence.main import app


COLLECTION_PATH = (
    Path(__file__).resolve().parents[3]
    / "postman"
    / "match-intelligence.postman_collection.json"
)
COLLECTION = json.loads(COLLECTION_PATH.read_text(encoding="utf-8"))
ITEMS = [item for group in COLLECTION["item"] for item in group["item"]]


@pytest.mark.parametrize("item", ITEMS, ids=[item["name"] for item in ITEMS])
def test_postman_request_matches_http_route(item):
    request = item["request"]
    path = request["url"].replace("{{baseUrl}}", "")
    body = request.get("body")
    response = TestClient(app).request(
        request["method"],
        path,
        json=json.loads(body["raw"]) if body else None,
    )
    scripts = [line for event in item["event"] for line in event["script"]["exec"]]
    expected = re.search(r"have\.status\((\d+)\)", "\n".join(scripts))
    assert expected, f"Postman request {item['name']} has no status assertion"
    assert response.status_code == int(expected.group(1)), response.text
    assert response.headers["content-type"].startswith("application/json")


def test_collection_covers_every_api_operation():
    documented = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }
    covered = {
        (
            item["request"]["method"],
            item["request"]["url"].replace("{{baseUrl}}", "").split("?", 1)[0],
        )
        for item in ITEMS
    }
    assert covered == documented


def test_azure_route_explains_missing_configuration(monkeypatch):
    for name in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    body = json.loads((Path(__file__).parent / "fixtures" / "narrative_match.json").read_text())
    response = TestClient(app).post(
        "/api/v1/narratives/live",
        json={
            "snapshot": body["snapshot"],
            "candidate": body["candidates"][0],
            "preferences": {"language": "es", "mode": "casual", "level": "normal"},
        },
    )
    assert response.status_code == 503
    assert "AZURE_OPENAI_ENDPOINT" in response.json()["detail"]
