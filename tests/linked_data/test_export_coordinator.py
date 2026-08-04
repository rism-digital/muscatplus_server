# ruff: noqa: S101

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from linked_data import export_coordinator


def make_args(tmp_path: Path) -> Namespace:
    return Namespace(
        export_dir=tmp_path,
        remote_host="example.org",
        remote_user="deployer",
        remote_port=2222,
        remote_key_path="/tmp/id_ed25519",
        remote_dir="/data/qlever-index/rism",
        tmux_session="rism-qlever-reindex",
        verbose=False,
        dry_run=False,
    )


def test_clear_generated_export_removes_only_generated_files(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    person_dir = tmp_path / "person"
    source_dir.mkdir(parents=True)
    person_dir.mkdir(parents=True)
    generated_paths = [
        source_dir / "part-00000.nt",
        source_dir / "part-00000.nt.tmp",
        source_dir / "failed-records-00000.jsonl",
        tmp_path / "manifest.json",
        tmp_path / export_coordinator.ONTOLOGY_TTL_NAME,
        tmp_path / export_coordinator.ONTOLOGY_NT_NAME,
    ]
    keep_paths = [
        source_dir / "notes.txt",
        tmp_path / "triples.gz",
        tmp_path / "README.txt",
    ]

    for path in [*generated_paths, *keep_paths]:
        path.write_text("x")

    export_coordinator.clear_generated_export(tmp_path)

    for path in generated_paths:
        assert not path.exists()
    for path in keep_paths:
        assert path.exists()


def test_remove_existing_triples_is_best_effort(tmp_path: Path) -> None:
    export_coordinator.remove_existing_triples(tmp_path)

    triples_path = export_coordinator.triples_gz_path(tmp_path)
    triples_path.write_text("x")

    export_coordinator.remove_existing_triples(tmp_path)

    assert not triples_path.exists()


def test_remove_existing_triples_dry_run_does_not_delete(tmp_path: Path) -> None:
    triples_path = export_coordinator.triples_gz_path(tmp_path)
    triples_path.write_text("x")

    export_coordinator.remove_existing_triples(tmp_path, dry_run=True)

    assert triples_path.exists()


def test_build_remote_reindex_script_contains_marker_and_service_commands() -> None:
    remote = export_coordinator.RemoteConfig(
        host="example.org",
        user="deployer",
        port=22,
        key_path=None,
        remote_dir="/data/qlever-index/rism",
        tmux_session="rism-qlever-reindex",
    )

    script = export_coordinator.build_remote_reindex_script(remote)
    launcher = export_coordinator.build_remote_tmux_launcher_script(remote)

    assert "trap 'rm -f /data/qlever-index/rism/.reindexing' EXIT" in script
    assert "touch /data/qlever-index/rism/.reindexing" in script
    assert "systemctl stop qlever" in script
    assert "qlever index --overwrite-existing --stxxl-memory 5G" in script
    assert "systemctl start qlever" in script
    assert "tmux kill-session -t rism-qlever-reindex" in launcher
    assert "tmux new-session -d -s rism-qlever-reindex" in launcher


def test_run_pipeline_invokes_expected_steps_in_order(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        export_coordinator,
        "remove_existing_triples",
        lambda export_dir, dry_run=False: calls.append(("remove", (export_dir, dry_run))),
    )
    monkeypatch.setattr(
        export_coordinator,
        "clear_generated_export",
        lambda export_dir, dry_run=False: calls.append(("clear", (export_dir, dry_run))),
    )
    monkeypatch.setattr(
        export_coordinator,
        "export_ontology",
        lambda export_dir, dry_run=False: calls.append(("ontology", (export_dir, dry_run))),
    )
    monkeypatch.setattr(
        export_coordinator,
        "export_linked_data",
        lambda export_dir, dry_run=False: calls.append(("data", (export_dir, dry_run))),
    )
    monkeypatch.setattr(
        export_coordinator,
        "build_triples_gz",
        lambda export_dir, dry_run=False: calls.append(("concat", (export_dir, dry_run))),
    )
    monkeypatch.setattr(
        export_coordinator,
        "upload_triples",
        lambda export_dir, remote, dry_run=False: calls.append(("upload", (export_dir, remote, dry_run))),
    )
    monkeypatch.setattr(
        export_coordinator,
        "start_remote_reindex",
        lambda remote, dry_run=False: calls.append(("reindex", (remote, dry_run))),
    )

    args = make_args(tmp_path)
    export_coordinator.run_pipeline(args)

    assert [name for name, _ in calls] == [
        "remove",
        "clear",
        "ontology",
        "data",
        "concat",
        "upload",
        "reindex",
    ]


def test_run_pipeline_dry_run_skips_directory_creation(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    export_dir = tmp_path / "missing-export-dir"
    args = make_args(export_dir)
    args.export_dir = export_dir
    args.dry_run = True

    monkeypatch.setattr(
        export_coordinator,
        "remove_existing_triples",
        lambda export_dir, dry_run=False: calls.append(("remove", dry_run)),
    )
    monkeypatch.setattr(
        export_coordinator,
        "clear_generated_export",
        lambda export_dir, dry_run=False: calls.append(("clear", dry_run)),
    )
    monkeypatch.setattr(
        export_coordinator,
        "export_ontology",
        lambda export_dir, dry_run=False: calls.append(("ontology", dry_run)),
    )
    monkeypatch.setattr(
        export_coordinator,
        "export_linked_data",
        lambda export_dir, dry_run=False: calls.append(("data", dry_run)),
    )
    monkeypatch.setattr(
        export_coordinator,
        "build_triples_gz",
        lambda export_dir, dry_run=False: calls.append(("concat", dry_run)),
    )
    monkeypatch.setattr(
        export_coordinator,
        "upload_triples",
        lambda export_dir, remote, dry_run=False: calls.append(("upload", dry_run)),
    )
    monkeypatch.setattr(
        export_coordinator,
        "start_remote_reindex",
        lambda remote, dry_run=False: calls.append(("reindex", dry_run)),
    )

    export_coordinator.run_pipeline(args)

    assert not export_dir.exists()
    assert calls == [
        ("remove", True),
        ("clear", True),
        ("ontology", True),
        ("data", True),
        ("concat", True),
        ("upload", True),
        ("reindex", True),
    ]


def test_remote_config_uses_env_fallback_for_key_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(export_coordinator.REMOTE_KEY_ENV_VAR, "/tmp/from-env")
    args = make_args(tmp_path)
    args.remote_key_path = None

    remote = export_coordinator.remote_config_from_args(args)

    assert remote.key_path == Path("/tmp/from-env")


def test_run_command_dry_run_skips_subprocess(monkeypatch) -> None:
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(export_coordinator.subprocess, "run", fake_run)

    export_coordinator.run_command(["echo", "hello"], dry_run=True)

    assert not called
