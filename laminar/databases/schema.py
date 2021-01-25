import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Status(Base):  # type: ignore
    __tablename__ = "status"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    execution = sa.Column(sa.Integer, sa.ForeignKey("execution.id"))
    step = sa.Column(sa.Integer, sa.ForeignKey("step.id"))
    status = sa.Column(sa.String, nullable=False)

    executions = relationship("Execution", back_populates="statuses")
    steps = relationship("Step", back_populates="status")


class Step(Base):  # type: ignore
    __tablename__ = "step"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String, nullable=False)
    flow = sa.Column(sa.Integer, sa.ForeignKey("flow.id"))
    payload = sa.Column(sa.JSON, nullable=False)

    flows = relationship("Flow", back_populates="steps")
    status = relationship("Status", order_by=Status.id, back_populates="steps")


class Execution(Base):  # type: ignore
    __tablename__ = "execution"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String, nullable=False)
    flow = sa.Column(sa.Integer, sa.ForeignKey("flow.id"))

    flows = relationship("Flow", back_populates="executions")
    statuses = relationship("Status", order_by=Status.id, back_populates="executions")


class Flow(Base):  # type: ignore
    __tablename__ = "flow"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String, nullable=False)
    project = sa.Column(sa.String, nullable=False)

    executions = relationship("Execution", order_by=Execution.id, back_populates="flows")
    steps = relationship("Step", order_by=Step.id, back_populates="flows")
