from http import HTTPStatus

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_docs_are_served_under_api() -> None:
    response = client.get("/api/docs")

    assert response.status_code == HTTPStatus.OK
    assert "/api/openapi.json" in response.text


def test_every_route_is_under_api() -> None:
    # The static web mount has path "", everything else must live under /api.
    paths = [p for route in app.routes if (p := getattr(route, "path", ""))]

    assert all(path.startswith("/api/") for path in paths)


def test_every_route_and_field_is_described() -> None:
    schema = client.get("/api/openapi.json").json()

    operations = [op for path in schema["paths"].values() for op in path.values()]
    assert operations
    assert all(op.get("description") for op in operations)
    for name, model in schema["components"]["schemas"].items():
        if name in {"HTTPValidationError", "ValidationError"}:
            continue
        # Enums such as Desk have no fields.
        fields = model.get("properties", {}).values()
        assert all(field.get("description") for field in fields), name
