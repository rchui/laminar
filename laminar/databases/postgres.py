"""Postgres for laminar flows."""

import multiprocessing
import os

from psycopg2.pool import ThreadedConnectionPool
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session as Session
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from laminar import configs, databases


class Client:
    _engine: Engine = None
    _pool: ThreadedConnectionPool = None
    _sessionmaker: sessionmaker = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            uri = databases.uri()
            if uri.startswith("sqlite://"):
                # Allows us to use the in-memory sqlite engine.
                self._engine = create_engine(
                    uri, connect_args={"check_same_thread": False}, poolclass=StaticPool, echo=True
                )
            else:
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

    @property
    def sessionmaker(self) -> sessionmaker:
        if self._sessionmaker is None:
            self._sessionmaker = sessionmaker(bind=self.engine)
        return self._sessionmaker

    def session(self) -> Session:
        return scoped_session(self.sessionmaker)


client = Client()
