import nox


@nox.session(python=False)
def pytest(session: nox.Session) -> None:
    session.run("pytest", "--version")
    session.run(
        "pytest",
        "-v",
        "--cov=laminar",
        "--cov-report=term-missing",
        "tests",
        env={"LAMINAR_POSTGRES_URI": "sqlite:///:memory:"},
    )


@nox.session(python=False)
def black(session: nox.Session) -> None:
    session.run("black", "--version")
    session.run("black", "--check", ".")


@nox.session(python=False)
def flake8(session: nox.Session) -> None:
    session.run("flake8", "--version")
    session.run("flake8", ".")


@nox.session(python=False)
def isort(session: nox.Session) -> None:
    session.run("isort", "--version")
    session.run("isort", "--check", ".")


@nox.session(python=False)
def mypy(session: nox.Session) -> None:
    session.run("mypy", "--version")
    session.run("mypy", "--allow-untyped-decorators", "--allow-subclassing-any", "--strict", ".")
