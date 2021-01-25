"""Unit tests for laminar.api.flows"""

import pytest
from fastapi.testclient import TestClient
from testing.postgresql import PostgresqlFactory

from laminar.api import app
from laminar.databases import postgres, schema


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# Generate Postgresql class which shares the generated database
Postgresql = PostgresqlFactory(cache_initialized_db=True)


@pytest.fixture(scope="function")
def pg() -> postgres.Session:
    with Postgresql() as pg:
        engine = postgres.client.engine(uri=pg.url())
        schema.Base.metadata.create_all(engine)
        yield postgres.client.session(uri=pg.url())
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

    response = client.get("/flows")
    assert response.status_code == 200
    assert response.json() == test_flows
