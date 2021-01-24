"""Database modules for laminar flows"""

from laminar import configs


def user_info() -> str:
    return f"{configs.postgres.user}:{configs.postgres.password}"


def machine_info() -> str:
    return f"{configs.postgres.host}:{configs.postgres.port}"


def authority() -> str:
    return f"{user_info()}@{machine_info()}"


def uri() -> str:
    return f"{configs.database.scheme}://{authority()}"
