"""Unit tests for laminar.api.flows"""

from typing import List

import pytest
from fastapi.testclient import TestClient
from testing.postgresql import PostgresqlFactory

from laminar.api import app
from laminar.databases import postgres, schema


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


Postgresql = PostgresqlFactory(cache_initialized_db=True)


@pytest.fixture(scope="function")
def pg() -> postgres.Session:
    with Postgresql() as pg:
        engine = postgres.client.engine(uri=pg.url(), new=True)
        schema.Base.metadata.create_all(engine)
        yield postgres.client.session(uri=pg.url(), new=True)
        Postgresql.clear_cache()


def test_get_flows(pg: postgres.Session, client: TestClient) -> None:
    test_flows = [
        {"id": 1, "name": "1", "project": "1"},
        {"id": 2, "name": "2", "project": "1"},
        {"id": 3, "name": "1", "project": "2"},
    ]
    for flow in test_flows:
        pg.add(schema.Flow(**flow))
    pg.commit()

    response = client.get("/flows/")
    assert response.status_code == 200
    assert response.json() == test_flows


def test_create_flow(pg: postgres.Session, client: TestClient) -> None:
    data = {"id": 1, "name": "test-name", "project": "test-project"}
    response = client.post("/flows/", json=data)
    assert response.status_code == 201
    assert response.json() == data

    rows: List[schema.Flow] = pg.query(schema.Flow).filter(schema.Flow.name == "test-name").all()
    assert len(rows) == 1
    [row] = rows
    assert row.name == "test-name"
    assert row.project == "test-project"


def test_get_flow(pg: postgres.Session, client: TestClient) -> None:
    test_flow = {"id": 1, "name": "test-name", "project": "test-project"}
    pg.add(schema.Flow(**test_flow))
    pg.commit()

    response = client.get("/flows/1/")
    assert response.status_code == 200
    assert response.json() == test_flow
