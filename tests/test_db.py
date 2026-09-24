import pytest

from tradegpt import db


@pytest.mark.parametrize("from_environment", [False, True])
@pytest.mark.parametrize(
    ("url", "expected_driver"),
    [
        ("postgresql://user:p%40ss@localhost/tradegpt?connect_timeout=3", "postgresql+psycopg"),
        ("postgresql+psycopg://user:p%40ss@localhost/tradegpt?connect_timeout=3", "postgresql+psycopg"),
        ("sqlite://", "sqlite"),
    ],
)
def test_make_engine_selects_driver(url, expected_driver, from_environment, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url)
    engine = db.make_engine() if from_environment else db.make_engine(url)
    try:
        assert engine.url.drivername == expected_driver
        if expected_driver == "postgresql+psycopg":
            assert engine.dialect.driver == "psycopg"
            assert engine.url.password == "p@ss"
            assert engine.url.query == {"connect_timeout": "3"}
        else:
            with engine.connect() as connection:
                assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
        assert db.database_url() == url
    finally:
        engine.dispose()


@pytest.mark.parametrize("url", ["postgresql+psycopg2://localhost/db", "mysql+pymysql://localhost/db"])
def test_make_engine_preserves_other_driver_urls(url, monkeypatch):
    calls = []
    sentinel = object()

    def capture_create_engine(value, **kwargs):
        calls.append((value, kwargs))
        return sentinel

    monkeypatch.setattr(db, "create_engine", capture_create_engine)
    assert db.make_engine(url) is sentinel
    assert calls == [(url, {"pool_pre_ping": True})]
