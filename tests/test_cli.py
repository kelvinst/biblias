import json as _json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

import cli

runner = CliRunner()


def _make_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE verse (id INTEGER, book_id INTEGER, chapter INTEGER, verse INTEGER, text TEXT)")
    con.execute("INSERT INTO verse VALUES (1, 20, 10, 4, 'As mãos preguiçosas...')")
    con.commit()
    con.close()


def test_help_lists_commands():
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    assert "fetch" in result.stdout
    assert "build" in result.stdout


def test_fetch_then_build(tmp_path: Path, monkeypatch):
    sql_dir = tmp_path / "inst" / "sql"
    sql_dir.mkdir(parents=True)
    _make_db(sql_dir / "KJA.sqlite")

    canon_dir = tmp_path / "data" / "canonical"
    dist_dir = tmp_path / "dist"
    monkeypatch.setattr(cli, "SQL_DIR", sql_dir)
    monkeypatch.setattr(cli, "CANON_DIR", canon_dir)
    monkeypatch.setattr(cli, "CORRECTIONS_DIR", tmp_path / "data" / "corrections")

    r1 = runner.invoke(cli.app, ["fetch", "KJA"])
    assert r1.exit_code == 0
    assert (canon_dir / "KJA" / "PRO.json").exists()

    r2 = runner.invoke(cli.app, ["build", "KJA", "--out", str(dist_dir)])
    assert r2.exit_code == 0
    assert (dist_dir / "KJA.xml").exists()


def test_fetch_refuses_when_corrections_exist(tmp_path: Path, monkeypatch):
    sql_dir = tmp_path / "inst" / "sql"
    sql_dir.mkdir(parents=True)
    _make_db(sql_dir / "KJA.sqlite")
    corr_dir = tmp_path / "data" / "corrections"
    corr_dir.mkdir(parents=True)
    (corr_dir / "KJA.json").write_text(_json.dumps([{"book": "PRO", "chapter": 10, "verse": 4}]))

    monkeypatch.setattr(cli, "SQL_DIR", sql_dir)
    monkeypatch.setattr(cli, "CANON_DIR", tmp_path / "data" / "canonical")
    monkeypatch.setattr(cli, "CORRECTIONS_DIR", corr_dir)

    blocked = runner.invoke(cli.app, ["fetch", "KJA"])
    assert blocked.exit_code != 0

    forced = runner.invoke(cli.app, ["fetch", "KJA", "--force"])
    assert forced.exit_code == 0


def test_build_multiple_formats(tmp_path: Path, monkeypatch):
    sql_dir = tmp_path / "inst" / "sql"
    sql_dir.mkdir(parents=True)
    _make_db(sql_dir / "KJA.sqlite")
    canon_dir = tmp_path / "data" / "canonical"
    dist_dir = tmp_path / "dist"
    monkeypatch.setattr(cli, "SQL_DIR", sql_dir)
    monkeypatch.setattr(cli, "CANON_DIR", canon_dir)
    monkeypatch.setattr(cli, "CORRECTIONS_DIR", tmp_path / "data" / "corrections")

    runner.invoke(cli.app, ["fetch", "KJA"])
    r = runner.invoke(cli.app, ["build", "KJA", "--format", "zefania,sqlite,json,markdown", "--out", str(dist_dir)])
    assert r.exit_code == 0
    assert (dist_dir / "KJA.xml").exists()
    assert (dist_dir / "KJA.sqlite").exists()
    assert (dist_dir / "KJA.json").exists()
    assert (dist_dir / "KJA" / "3-OT-Wisdom" / "KJA-20-PRO"
            / "KJA-20-PRO-010.md").exists()


def test_build_all_versions(tmp_path: Path, monkeypatch):
    sql_dir = tmp_path / "inst" / "sql"
    sql_dir.mkdir(parents=True)
    _make_db(sql_dir / "KJA.sqlite")
    _make_db(sql_dir / "NVI.sqlite")
    canon_dir = tmp_path / "data" / "canonical"
    dist_dir = tmp_path / "dist"
    monkeypatch.setattr(cli, "SQL_DIR", sql_dir)
    monkeypatch.setattr(cli, "CANON_DIR", canon_dir)
    monkeypatch.setattr(cli, "CORRECTIONS_DIR", tmp_path / "data" / "corrections")

    runner.invoke(cli.app, ["fetch", "KJA"])
    runner.invoke(cli.app, ["fetch", "NVI"])

    r = runner.invoke(cli.app, ["build", "--out", str(dist_dir)])
    assert r.exit_code == 0
    assert (dist_dir / "KJA.xml").exists()
    assert (dist_dir / "NVI.xml").exists()

    explicit = runner.invoke(cli.app, ["build", "all", "--out", str(tmp_path / "dist2")])
    assert explicit.exit_code == 0
    assert (tmp_path / "dist2" / "KJA.xml").exists()
    assert (tmp_path / "dist2" / "NVI.xml").exists()


def test_build_version_list(tmp_path: Path, monkeypatch):
    sql_dir = tmp_path / "inst" / "sql"
    sql_dir.mkdir(parents=True)
    for code in ("KJA", "NVI", "ACF"):
        _make_db(sql_dir / f"{code}.sqlite")
    canon_dir = tmp_path / "data" / "canonical"
    dist_dir = tmp_path / "dist"
    monkeypatch.setattr(cli, "SQL_DIR", sql_dir)
    monkeypatch.setattr(cli, "CANON_DIR", canon_dir)
    monkeypatch.setattr(cli, "CORRECTIONS_DIR", tmp_path / "data" / "corrections")

    for code in ("KJA", "NVI", "ACF"):
        runner.invoke(cli.app, ["fetch", code])

    r = runner.invoke(cli.app, ["build", "KJA, NVI", "--out", str(dist_dir)])
    assert r.exit_code == 0
    assert (dist_dir / "KJA.xml").exists()
    assert (dist_dir / "NVI.xml").exists()
    assert not (dist_dir / "ACF.xml").exists()


def test_build_rejects_unknown_version(tmp_path: Path, monkeypatch):
    sql_dir = tmp_path / "inst" / "sql"
    sql_dir.mkdir(parents=True)
    _make_db(sql_dir / "KJA.sqlite")
    canon_dir = tmp_path / "data" / "canonical"
    monkeypatch.setattr(cli, "SQL_DIR", sql_dir)
    monkeypatch.setattr(cli, "CANON_DIR", canon_dir)
    monkeypatch.setattr(cli, "CORRECTIONS_DIR", tmp_path / "data" / "corrections")

    runner.invoke(cli.app, ["fetch", "KJA"])
    r = runner.invoke(cli.app, ["build", "KJA,NOPE", "--out", str(tmp_path / "dist")])
    assert r.exit_code != 0


def test_build_without_canonical_fails(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cli, "CANON_DIR", tmp_path / "data" / "canonical")
    r = runner.invoke(cli.app, ["build", "--out", str(tmp_path / "dist")])
    assert r.exit_code != 0


def test_build_rejects_canonical_without_meta(tmp_path: Path, monkeypatch):
    sql_dir = tmp_path / "inst" / "sql"
    sql_dir.mkdir(parents=True)
    _make_db(sql_dir / "KJA.sqlite")
    canon_dir = tmp_path / "data" / "canonical"
    monkeypatch.setattr(cli, "SQL_DIR", sql_dir)
    monkeypatch.setattr(cli, "CANON_DIR", canon_dir)
    monkeypatch.setattr(cli, "CORRECTIONS_DIR", tmp_path / "data" / "corrections")

    runner.invoke(cli.app, ["fetch", "KJA"])
    half = canon_dir / "XYZ"
    half.mkdir()
    (half / "PRO.json").write_text("{}")

    r = runner.invoke(cli.app, ["build", "--out", str(tmp_path / "dist")])
    assert r.exit_code != 0
    assert "XYZ" in r.output

    named = runner.invoke(cli.app, ["build", "XYZ", "--out", str(tmp_path / "dist")])
    assert named.exit_code != 0
    assert "XYZ" in named.output

    # A half-written version is not a reason to refuse the ones that are whole.
    other = runner.invoke(cli.app, ["build", "KJA", "--out", str(tmp_path / "dist")])
    assert other.exit_code == 0
    assert (tmp_path / "dist" / "KJA.xml").exists()
