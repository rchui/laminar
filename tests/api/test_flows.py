"""Unit tests for laminar.api.flows"""

from typing import List

from fastapi.testclient import TestClient

from laminar.databases import postgres, schema


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


def test_get_executions(pg: postgres.Session, client: TestClient) -> None:
    test_flow = {"id": 1, "name": "test-name", "project": "test-project"}
    test_executions = [
        {"id": 1, "name": "test-name", "flow": 1},
        {"id": 2, "name": "test-name", "flow": 1},
        {"id": 3, "name": "test-name", "flow": 1},
    ]

    pg.add(schema.Flow(**test_flow))
    for execution in test_executions:
        pg.add(schema.Execution(**execution))
    pg.commit()

    response = client.get("/flows/1/executions/")
    assert response.status_code == 200
    assert response.json() == test_executions


def test_get_execution(pg: postgres.Session, client: TestClient) -> None:
    test_flow = {"id": 1, "name": "test-name", "project": "test-project"}
    test_execution = {"id": 1, "name": "test-name", "flow": 1}

    pg.add(schema.Flow(**test_flow))
    pg.add(schema.Execution(**test_execution))
    pg.commit()

    response = client.get("/flows/1/executions/1/")
    assert response.status_code == 200
    assert response.json() == test_execution


def test_get_tasks(pg: postgres.Session, client: TestClient) -> None:
    test_flow = {"id": 1, "name": "test-name", "project": "test-project"}
    test_tasks = [
        {"id": 1, "name": "test-name", "flow": 1, "payload": {}},
        {"id": 2, "name": "test-name", "flow": 1, "payload": {}},
        {"id": 3, "name": "test-name", "flow": 1, "payload": {}},
    ]

    pg.add(schema.Flow(**test_flow))
    for task in test_tasks:
        pg.add(schema.Task(**task))
    pg.commit()

    response = client.get("/flows/1/tasks")
    assert response.status_code == 200
    assert response.json() == test_tasks


def test_get_task(pg: postgres.Session, client: TestClient) -> None:
    test_flow = {"id": 1, "name": "test-name", "project": "test-project"}
    test_task = {"id": 1, "name": "test-name", "flow": 1, "payload": {}}

    pg.add(schema.Flow(**test_flow))
    pg.add(schema.Task(**test_task))
    pg.commit()

    response = client.get("/flows/1/tasks/1/")
    assert response.status_code == 200
    assert response.json() == test_task
