"""Regression coverage for CI database connection parsing."""

from packages.storage.database import database_connection_params


def test_database_connection_params_separate_user_and_password():
    params = database_connection_params(
        "postgresql+asyncpg://runner:test@localhost:5432/sourceos_test"
    )

    assert params == {
        "user": "runner",
        "password": "test",
        "host": "localhost",
        "port": 5432,
        "database": "sourceos_test",
    }
