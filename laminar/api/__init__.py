from fastapi import FastAPI, status

from laminar.api import flows

app = FastAPI()
app.include_router(flows.router)


@app.get("/healthz", status_code=status.HTTP_200_OK)
def healthz() -> None:
    """Health check."""
    ...
