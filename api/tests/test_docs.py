from http import HTTPStatus

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_docs_are_served_under_api() -> None:
    response = client.get("/api/docs")

    assert response.status_code == HTTPStatus.OK
    assert "/api/openapi.json" in response.text


def test_docs_are_not_served_at_fastapi_defaults() -> None:
    paths = {getattr(route, "path", None) for route in app.routes}

    assert {"/docs", "/redoc", "/openapi.json"}.isdisjoint(paths)


def test_every_route_and_field_is_described() -> None:
    schema = client.get("/api/openapi.json").json()

    operations = [op for path in schema["paths"].values() for op in path.values()]
    assert operations
    assert all(op.get("description") for op in operations)
    for model in schema["components"]["schemas"].values():
        if model["title"] in {"HTTPValidationError", "ValidationError"}:
            continue
        assert all(field.get("description") for field in model["properties"].values())
