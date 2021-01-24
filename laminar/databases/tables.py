import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Flow(Base):  # type: ignore
    __tablename__ = "flow"

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    project = sa.Column(sa.String, nullable=False)
    version = sa.Column(sa.Integer, nullable=False)
