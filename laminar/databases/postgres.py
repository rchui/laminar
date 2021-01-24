"""Postgres for laminar flows."""

import multiprocessing
import os

from psycopg2.pool import ThreadedConnectionPool
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session, sessionmaker

from laminar import configs, databases


class Client:
    _engine: Engine = None
    _pool: ThreadedConnectionPool = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(databases.uri(), echo=True)
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

    def session(self) -> Session:
        return sessionmaker(bind=self.engine)


client = Client()
