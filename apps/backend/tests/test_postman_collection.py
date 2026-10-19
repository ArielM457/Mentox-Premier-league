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


def _collection_token() -> str:
    """Hace lo mismo que Postman: ejecuta la petición que guarda {{token}} y devuelve su valor."""
    login = next(
        item for item in ITEMS
        if any("collectionVariables.set('token'" in line for event in item["event"] for line in event["script"]["exec"])
    )
    request = login["request"]
    response = TestClient(app).post(request["url"].replace("{{baseUrl}}", ""), json=json.loads(request["body"]["raw"]))
    return response.json()["token"]


@pytest.mark.parametrize("item", ITEMS, ids=[item["name"] for item in ITEMS])
def test_postman_request_matches_http_route(item):
    request = item["request"]
    path = request["url"].replace("{{baseUrl}}", "")
    body = request.get("body")
    headers = {header["key"]: header["value"] for header in request.get("header", [])}
    if any("{{token}}" in value for value in headers.values()):
        token = _collection_token()
        headers = {key: value.replace("{{token}}", token) for key, value in headers.items()}
    response = TestClient(app).request(
        request["method"],
        path,
        json=json.loads(body["raw"]) if body else None,
        headers=headers,
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
    requested = {
        (
            item["request"]["method"],
            item["request"]["url"].replace("{{baseUrl}}", "").split("?", 1)[0],
        )
        for item in ITEMS
    }

    def template(path: str) -> re.Pattern[str]:
        # Las rutas con parámetros, como /matches/{match_id}, se prueban con valores concretos.
        parts = re.split(r"\{[^}]+\}", path)
        return re.compile("^" + "[^/]+".join(re.escape(part) for part in parts) + "$")

    covered = {
        (method, path)
        for method, path in documented
        if any(m == method and template(path).match(url) for m, url in requested)
    }
    assert covered == documented
    assert all(any(m == method and template(p).match(url) for method, p in documented) for m, url in requested)


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
