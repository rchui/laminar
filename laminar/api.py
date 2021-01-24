from fastapi import FastAPI, status
from starlette.responses import RedirectResponse

from laminar.databases import postgres
from laminar.queues import pq

app = FastAPI()
pq.client.pq
postgres.client.engine


@app.get("/healthz", status_code=status.HTTP_200_OK)
def healthz() -> None:
    ...


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/healthz")


@app.get("/jobs")
def get_jobs() -> None:
    ...
