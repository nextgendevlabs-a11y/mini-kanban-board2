from backend.main import Database


def sqlite_url(path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_workspace_snapshot_persists_between_database_instances(tmp_path) -> None:
    database_url = sqlite_url(tmp_path / "flowdeck.db")

    first = Database(database_url)
    created = first.create_board("Persisted board")
    board_id = created["team"]["boardIds"][-1]

    second = Database(database_url)
    snapshot = second.clone()

    assert snapshot["boards"][board_id]["name"] == "Persisted board"


def test_database_url_environment_variable_selects_engine(monkeypatch, tmp_path) -> None:
    database_url = sqlite_url(tmp_path / "configured.db")
    monkeypatch.setenv("DATABASE_URL", database_url)

    database = Database()

    assert database.database_url == database_url
    assert database.clone()["team"]["name"] == "Flowdeck Studio"
