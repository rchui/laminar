"""Unit test fixtures for laminar.api"""

import pytest
from fastapi.testclient import TestClient

from laminar.api import app
from laminar.databases import postgres, schema


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="function")
def pg() -> postgres.Session:
    # Create all database tables.
    schema.Base.metadata.create_all(postgres.client.engine)

    # Manually commit changes to ensure they've gone through.
    session = postgres.client.session()
    session.commit()
    yield session

    # Drop all database tables after tests.
    schema.Base.metadata.drop_all(postgres.client.engine)
