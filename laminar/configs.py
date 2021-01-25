"""Global config for laminar flows."""

from pydantic import BaseSettings, Field


class Database(BaseSettings):
    postgresql: str = "postgresql"
    scheme: str = Field(postgresql, env="LAMINAR_DATABASE_SCHEME")


class Execution(BaseSettings):
    agent: bool = Field(False, env="LAMINAR_EXECUTION_AGENT")
    step: str = Field(None, env="LAMINAR_EXECUTION_STEP")


class Postgres(BaseSettings):

    database: str = Field("laminar", env="LAMINAR_POSTGRES_DATABASE")
    host: str = Field("localhost", env="LAMINAR_POSTGRES_HOST")
    user: str = Field("laminar", env="LAMINAR_POSTGRES_USER")
    password: str = Field("laminar", env="LAMINAR_POSTGRESS_PASSWORD")
    port: str = Field("5432", env="LAMINAR_POSTGRES_PORT")
    uri: str = Field(None, env="LAMINAR_POSTGRES_URI")


class Workspace(BaseSettings):
    path: str = Field(None, env="LAMINAR_WORKSPACE_PATH")


database = Database()
execution = Execution()
postgres = Postgres()
workspace = Workspace()
