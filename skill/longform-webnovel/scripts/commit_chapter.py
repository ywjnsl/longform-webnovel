#!/usr/bin/env python3
"""Validate and commit a staged chapter update with backup and rollback."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from webnovel_io import backup_files, copy_file_atomic, load_json, restore_backup, utc_now, write_json_atomic


ALLOWED_TOP_LEVEL = {"project.json", "canon", "planning", "state", "chapters", "reviews", "sessions", "cast", "contracts", "intents"}
REQUIRED_STAGED = {
    "project.json",
    "state/story-state.json",
    "state/threads.json",
    "state/rewards.json",
    "state/cast-arcs.json",
}


def collect_staged_files(staging: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in staging.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not allowed in staging: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(staging)
        if relative.parts[0] not in ALLOWED_TOP_LEVEL:
            raise ValueError(f"Staged path is not allowed: {relative}")
        files[relative.as_posix()] = path
    missing = sorted(REQUIRED_STAGED - set(files))
    if missing:
        raise ValueError(f"Staging is missing required files: {', '.join(missing)}")
    return files


def link_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if not source.is_dir():
        return
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file() and not path.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(path, target)
            except OSError:
                shutil.copy2(path, target)


def build_shadow(root: Path, staged: dict[str, Path]) -> Path:
    transaction_root = root / ".webnovel" / "transactions"
    transaction_root.mkdir(parents=True, exist_ok=True)
    shadow = Path(tempfile.mkdtemp(prefix="preview-", dir=transaction_root))

    shutil.copy2(root / "project.json", shadow / "project.json")
    # The validator checks completed market research against its dated snapshot.
    # Keep research in the shadow project so a normal chapter commit does not
    # require temporarily downgrading an otherwise valid project.
    for name in ("canon", "planning", "state", "research", "cast", "contracts", "intents"):
        if (root / name).is_dir():
            shutil.copytree(root / name, shadow / name)
    for name in ("chapters", "reviews", "sessions"):
        link_tree(root / name, shadow / name)

    for relative, source in staged.items():
        copy_file_atomic(source, shadow / relative)

    project = load_json(shadow / "project.json")
    project["updatedAt"] = utc_now()
    write_json_atomic(shadow / "project.json", project)
    return shadow


def run_validation(shadow: Path) -> dict:
    validator = Path(__file__).with_name("validate_project.py")
    completed = subprocess.run(
        [sys.executable, str(validator), str(shadow)],
        check=False,
        text=True,
        capture_output=True,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Validator returned invalid output: {completed.stdout or completed.stderr}") from exc
    if completed.returncode != 0 or not result.get("ok"):
        raise ValueError(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def acquire_lock(root: Path) -> tuple[int, Path]:
    lock = root / ".webnovel" / "commit.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(f"Project is locked by another commit: {lock}") from exc
    os.write(descriptor, f"pid={os.getpid()} time={utc_now()}\n".encode())
    os.fsync(descriptor)
    return descriptor, lock


def release_lock(descriptor: int, lock: Path) -> None:
    os.close(descriptor)
    lock.unlink(missing_ok=True)


def validate_transition(root: Path, staged: dict[str, Path], allow_revision: bool) -> int:
    current = load_json(root / "project.json")
    proposed = load_json(staged["project.json"])
    old_committed = current.get("lastCommittedChapter")
    new_committed = proposed.get("lastCommittedChapter")
    new_draft = proposed.get("latestDraftChapter")
    if not all(isinstance(value, int) and value >= 0 for value in (old_committed, new_committed, new_draft)):
        raise ValueError("Invalid project chapter counters")
    if new_committed != new_draft:
        raise ValueError("A chapter commit must align latestDraftChapter and lastCommittedChapter")
    current_story = current.get("shortStory") if isinstance(current.get("shortStory"), dict) else {}
    proposed_story = proposed.get("shortStory") if isinstance(proposed.get("shortStory"), dict) else {}
    if (
        proposed_story.get("status") == "complete"
        and current_story.get("status") != "complete"
        and "reviews/final-review.json" not in staged
    ):
        raise ValueError("Completing a short story requires staged reviews/final-review.json")
    if allow_revision:
        if new_committed not in {old_committed, old_committed + 1}:
            raise ValueError("Revision mode may keep the current chapter or advance by one")
    elif new_committed != old_committed + 1:
        raise ValueError(f"Normal commit must advance exactly one chapter from {old_committed}")
    chapter_prefix = f"chapters/第{new_committed:04d}章-"
    if not any(relative.startswith(chapter_prefix) and relative.endswith(".md") for relative in staged):
        raise ValueError(f"Staging needs the chapter {new_committed}正文 file")
    for suffix in ("lint", "review"):
        review_path = f"reviews/第{new_committed:04d}章-{suffix}.json"
        if review_path not in staged:
            raise ValueError(f"Staging needs {review_path}")
    ensemble = proposed.get("ensemble") if isinstance(proposed.get("ensemble"), dict) else {}
    enforce_from = ensemble.get("enforceFromChapter", 1)
    enabled = ensemble.get("enabled", True)
    if enabled and isinstance(enforce_from, int) and new_committed >= enforce_from:
        contract_path = f"contracts/chapter-{new_committed:04d}.json"
        ruling_path = f"intents/chapter-{new_committed:04d}/ruling.json"
        if contract_path not in staged:
            raise ValueError(f"Ensemble chapter {new_committed} needs staged {contract_path}")
        if ruling_path not in staged:
            raise ValueError(f"Ensemble chapter {new_committed} needs staged {ruling_path}")
        if f"planning/current-arc.md" not in staged:
            raise ValueError("Ensemble chapter commit needs staged planning/current-arc.md")
    return new_committed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--staging", type=Path)
    operation.add_argument("--restore", type=Path)
    parser.add_argument("--allow-revision", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.project.expanduser().resolve()
    if not (root / "project.json").is_file():
        raise SystemExit(f"Not a webnovel project: {root}")
    descriptor, lock = acquire_lock(root)
    shadow = None
    try:
        if args.restore:
            if args.dry_run:
                raise ValueError("--dry-run is not supported with --restore")
            restore_backup(root, args.restore)
            result = run_validation(root)
            print(json.dumps({"restored": str(args.restore.resolve()), "validation": result}, ensure_ascii=False, indent=2))
            return 0

        staging = args.staging.expanduser().resolve()
        if not staging.is_dir():
            raise ValueError(f"Staging directory does not exist: {staging}")
        staged = collect_staged_files(staging)
        chapter = validate_transition(root, staged, args.allow_revision)
        shadow = build_shadow(root, staged)
        validation = run_validation(shadow)
        if args.dry_run:
            print(json.dumps({"ok": True, "dryRun": True, "chapter": chapter, "validation": validation}, ensure_ascii=False, indent=2))
            return 0

        relative_paths = [Path(relative) for relative in staged]
        backup = backup_files(root, relative_paths, f"chapter-{chapter:04d}")
        try:
            ordered = sorted(relative_paths, key=lambda item: (item.as_posix() == "project.json", item.as_posix()))
            for relative in ordered:
                copy_file_atomic(shadow / relative, root / relative)
        except Exception:
            restore_backup(root, backup)
            raise

        print(
            json.dumps(
                {"ok": True, "chapter": chapter, "backup": str(backup), "files": [path.as_posix() for path in ordered], "warnings": validation.get("warnings", [])},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        if shadow:
            shutil.rmtree(shadow, ignore_errors=True)
        release_lock(descriptor, lock)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)
