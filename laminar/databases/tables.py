import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Steps(Base):  # type: ignore
    __tablename__ = "steps"

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    execution = sa.Column(sa.Integer, sa.ForeignKey("executions.id"))
    payload = sa.Column(sa.JSON, nullable=False)
    status = sa.Column(sa.String, nullable=False)

    executions = relationship("Executions", back_populates="steps")


class Executions(Base):  # type: ignore
    __tablename__ = "executions"

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    flow = sa.Column(sa.Integer, sa.ForeignKey("flows.id"))
    status = sa.Column(sa.String, nullable=False)

    flows = relationship("Flows", back_populates="flows")
    steps = relationship("Steps", order_by=Steps.id, back_populates="steps")


class Flows(Base):  # type: ignore
    __tablename__ = "flows"

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    project = sa.Column(sa.String, nullable=False)
    version = sa.Column(sa.Integer, nullable=False)

    executions = relationship("Executions", order_by=Executions.id, back_populates="executions")
