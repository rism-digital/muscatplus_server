from __future__ import annotations

import argparse
import logging
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(PROJECT_ROOT))

from linked_data.export import RECORD_TYPES, clean_output_for_types

DEFAULT_EXPORT_DIR = Path("/data")
DEFAULT_REMOTE_DIR = "/data/qlever-index/rism"
DEFAULT_TMUX_SESSION = "rism-qlever-reindex"
REMOTE_KEY_ENV_VAR = "RISM_EXPORT_REMOTE_KEY_PATH"
ONTOLOGY_TTL_NAME = "rism-service-ontology.ttl"
ONTOLOGY_NT_NAME = "rism-service-ontology.nt"

log = logging.getLogger("ld_export_coordinator")


@dataclass(frozen=True)
class RemoteConfig:
    host: str
    user: str
    port: int
    key_path: Path | None
    remote_dir: str
    tmux_session: str


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def triples_gz_path(export_dir: Path) -> Path:
    return export_dir / "triples.gz"


def ontology_output_path(export_dir: Path, output_format: str) -> Path:
    ontology_name = ONTOLOGY_TTL_NAME if output_format == "ttl" else ONTOLOGY_NT_NAME
    return export_dir / ontology_name


def build_python_command(script_path: Path, *args: str) -> list[str]:
    return [sys.executable, str(script_path), *args]


def ssh_base_command(remote: RemoteConfig) -> list[str]:
    cmd = ["ssh", "-p", str(remote.port)]
    if remote.key_path is not None:
        cmd.extend(["-i", str(remote.key_path)])
    return cmd


def scp_command(local_path: Path, remote: RemoteConfig, remote_path: str) -> list[str]:
    cmd = ["scp", "-P", str(remote.port)]
    if remote.key_path is not None:
        cmd.extend(["-i", str(remote.key_path)])
    cmd.extend([str(local_path), f"{remote.user}@{remote.host}:{remote_path}"])
    return cmd


def ssh_command(remote: RemoteConfig, remote_script: str) -> list[str]:
    return [
        *ssh_base_command(remote),
        f"{remote.user}@{remote.host}",
        "bash",
        "-lc",
        remote_script,
    ]


def run_command(cmd: list[str], *, cwd: Path | None = None, dry_run: bool = False) -> None:
    display = " ".join(shlex.quote(part) for part in cmd)
    prefix = "Dry run:" if dry_run else "Running:"
    log.info("%s %s", prefix, display)
    if dry_run:
        return
    subprocess.run(cmd, cwd=cwd, check=True)


def remove_existing_triples(export_dir: Path, *, dry_run: bool = False) -> None:
    triples_path = triples_gz_path(export_dir)
    if dry_run:
        log.info("Dry run: would remove existing local triples.gz if present: %s", triples_path)
        return
    try:
        triples_path.unlink()
        log.info("Removed existing local triples.gz: %s", triples_path)
    except FileNotFoundError:
        log.info("No existing local triples.gz to remove: %s", triples_path)


def clear_generated_export(export_dir: Path, *, dry_run: bool = False) -> None:
    if dry_run:
        log.info("Dry run: would clear generated export files under: %s", export_dir)
        return
    clean_output_for_types(export_dir, RECORD_TYPES)

    for generated_file in (
        export_dir / "manifest.json",
        ontology_output_path(export_dir, "ttl"),
        ontology_output_path(export_dir, "nt"),
    ):
        try:
            generated_file.unlink()
        except FileNotFoundError:
            continue


def build_remote_preflight_script(remote: RemoteConfig) -> str:
    remote_dir = shlex.quote(remote.remote_dir)
    return "\n".join(
        [
            "set -euo pipefail",
            "command -v tmux >/dev/null",
            "command -v systemctl >/dev/null",
            "command -v qlever >/dev/null",
            f"mkdir -p {remote_dir}",
        ]
    )


def build_remote_reindex_script(remote: RemoteConfig) -> str:
    remote_dir = shlex.quote(remote.remote_dir)
    marker_path = shlex.quote(f"{remote.remote_dir}/.reindexing")
    return "\n".join(
        [
            "set -euo pipefail",
            f"cd {remote_dir}",
            f"trap 'rm -f {marker_path}' EXIT",
            f"touch {marker_path}",
            "systemctl stop qlever",
            "qlever index --overwrite-existing --stxxl-memory 5G",
            "systemctl start qlever",
        ]
    )


def build_remote_tmux_launcher_script(remote: RemoteConfig) -> str:
    session_name = shlex.quote(remote.tmux_session)
    index_script = build_remote_reindex_script(remote)
    tmux_command = shlex.quote(f"bash -lc {shlex.quote(index_script)}")
    return "\n".join(
        [
            "set -euo pipefail",
            f"tmux kill-session -t {session_name} 2>/dev/null || true",
            f"tmux new-session -d -s {session_name} {tmux_command}",
        ]
    )


def export_ontology(export_dir: Path, *, dry_run: bool = False) -> None:
    for output_format in ("nt", "ttl"):
        output_path = ontology_output_path(export_dir, output_format)
        run_command(
            build_python_command(
                SCRIPT_DIR / "generate_ontology.py",
                "--format",
                output_format,
                "--output",
                str(output_path),
            ),
            dry_run=dry_run,
        )


def export_linked_data(export_dir: Path, *, dry_run: bool = False) -> None:
    run_command(
        build_python_command(
            SCRIPT_DIR / "export.py",
            "--empty",
            "--output",
            str(export_dir),
        ),
        dry_run=dry_run,
    )


def build_triples_gz(export_dir: Path, *, dry_run: bool = False) -> None:
    run_command(
        ["bash", str(SCRIPT_DIR / "concat_nt.sh"), "--force", str(export_dir), str(triples_gz_path(export_dir))],
        dry_run=dry_run,
    )


def upload_triples(export_dir: Path, remote: RemoteConfig, *, dry_run: bool = False) -> None:
    run_command(
        scp_command(
            triples_gz_path(export_dir),
            remote,
            f"{remote.remote_dir}/triples.gz",
        ),
        dry_run=dry_run,
    )


def start_remote_reindex(remote: RemoteConfig, *, dry_run: bool = False) -> None:
    run_command(
        ssh_command(remote, build_remote_preflight_script(remote)),
        dry_run=dry_run,
    )
    run_command(
        ssh_command(remote, build_remote_tmux_launcher_script(remote)),
        dry_run=dry_run,
    )
    log.info(
        "%s remote tmux session '%s'. Inspect with: ssh -p %s %s@%s tmux capture-pane -pt %s",
        "Would start" if dry_run else "Started",
        remote.tmux_session,
        remote.port,
        remote.user,
        remote.host,
        remote.tmux_session,
    )


def parse_remote_key_path(raw_value: str | None) -> Path | None:
    if not raw_value:
        return None
    return Path(raw_value).expanduser()


def remote_config_from_args(args: argparse.Namespace) -> RemoteConfig:
    key_value = args.remote_key_path or os.environ.get(REMOTE_KEY_ENV_VAR)
    return RemoteConfig(
        host=args.remote_host,
        user=args.remote_user,
        port=args.remote_port,
        key_path=parse_remote_key_path(key_value),
        remote_dir=args.remote_dir,
        tmux_session=args.tmux_session,
    )


def run_pipeline(args: argparse.Namespace) -> None:
    export_dir = args.export_dir
    remote = remote_config_from_args(args)
    if args.dry_run:
        log.info("Dry run enabled: no local or remote changes will be made.")
    else:
        export_dir.mkdir(parents=True, exist_ok=True)

    remove_existing_triples(export_dir, dry_run=args.dry_run)
    clear_generated_export(export_dir, dry_run=args.dry_run)
    export_ontology(export_dir, dry_run=args.dry_run)
    export_linked_data(export_dir, dry_run=args.dry_run)
    build_triples_gz(export_dir, dry_run=args.dry_run)
    upload_triples(export_dir, remote, dry_run=args.dry_run)
    start_remote_reindex(remote, dry_run=args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run linked-data export locally and trigger a detached remote QLever reindex."
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help="Local export directory to rebuild before uploading.",
    )
    parser.add_argument("--remote-host", required=True, help="Remote host for upload and reindex.")
    parser.add_argument("--remote-user", required=True, help="Remote SSH user.")
    parser.add_argument("--remote-port", type=int, default=22, help="Remote SSH port.")
    parser.add_argument(
        "--remote-key-path",
        help=f"Optional SSH private key path. Falls back to ${REMOTE_KEY_ENV_VAR}.",
    )
    parser.add_argument(
        "--remote-dir",
        default=DEFAULT_REMOTE_DIR,
        help="Remote directory containing triples.gz and the QLever index.",
    )
    parser.add_argument(
        "--tmux-session",
        default=DEFAULT_TMUX_SESSION,
        help="Detached tmux session name for the remote reindex.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log the full export/upload/reindex workflow without making any local or remote changes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
    run_pipeline(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
