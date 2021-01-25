import nox

versions = ["3.6"]


@nox.session(python=versions)
def pytest(session: nox.Session) -> None:
    session.install("pytest", "pytest-cov")
    session.run("pytest", "--version")
    session.run("pytest", "--cov=laminar", "--cov-report=term-missing", "tests")


@nox.session(python="3.6")
def black(session: nox.Session) -> None:
    session.install("black")
    session.run("black", "--version")
    session.run("black", "--check", ".")


@nox.session(python="3.6")
def flake8(session: nox.Session) -> None:
    session.install("flake8")
    session.run("flake8", "--version")
    session.run("flake8", ".")


@nox.session(python="3.6")
def isort(session: nox.Session) -> None:
    session.install("isort")
    session.run("isort", "--version")
    session.run("isort", "--check", ".")


@nox.session(python="3.6")
def mypy(session: nox.Session) -> None:
    session.install("mypy")
    session.run("mypy", "--allow-untyped-decorators", "--allow-subclassing-any", "--strict", ".")
