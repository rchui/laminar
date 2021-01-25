"""Postgres for laminar flows."""

import multiprocessing
import os

from psycopg2.pool import ThreadedConnectionPool
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session as Session
from sqlalchemy.orm import sessionmaker

from laminar import configs, databases


class Client:
    _engine: Engine = None
    _pool: ThreadedConnectionPool = None
    _sessionmaker: sessionmaker = None

    def engine(self, *, uri: str) -> Engine:
        if self._engine is None:
            self._engine = create_engine(uri, echo=True)
        return self._engine

    @property
    def pool(self) -> ThreadedConnectionPool:
        if self._pool is None:
            self._pool = ThreadedConnectionPool(
                1,
                int(os.environ.get("WORKERS_PER_CORE", "2")) * multiprocessing.cpu_count(),
                dbname=configs.postgres.database,
                user=configs.postgres.user,
                password=configs.postgres.password,
                host=configs.postgres.host,
                port=configs.postgres.port,
            )
        return self._pool

    def sessionmaker(self, *, uri: str) -> sessionmaker:
        if self._sessionmaker is None:
            self._sessionmaker = sessionmaker(bind=self.engine(uri=uri))
        return self._sessionmaker

    def session(self, *, uri: str = None) -> Session:
        sessionmaker = self.sessionmaker(uri=uri or databases.uri())
        return sessionmaker()


client = Client()
