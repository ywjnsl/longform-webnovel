#!/usr/bin/env python3
"""Exercise recovery across commits and edits without adding draft facts to canon."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from chapter_cut import export_slices, suggest_cut
from draft_checkpoint import confirm, inspect, save


class DraftCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "project"
        self.root.mkdir()
        (self.root / "chapters").mkdir()
        self.set_chapter(0)
        self.source, self.head, self.tail = [Path(self.temporary.name) / name for name in ("source.md", "head.md", "tail.md")]
        self.raw = '他把灯递过去。\r\n\r\n她接住，朝门口照。\r\n'.encode()
        self.source.write_bytes(self.raw)
        self.head.write_bytes('他把灯递过去。\r\n\r\n'.encode())
        self.tail.write_bytes('她接住，朝门口照。\r\n'.encode())

    def set_chapter(self, chapter):
        (self.root / "project.json").write_text(json.dumps({"storyMode": "serial", "lastCommittedChapter": chapter}))

    def checkpoint(self):
        return save(self.root, 1, self.source, self.head, self.tail)

    def commit_first(self, body="他把灯递过去。"):
        path = self.root / "chapters/第0001章-门口.md"
        path.write_text('# 第一章 门口\n\n' + body + '\n')
        self.set_chapter(1)
        return path

    def test_recovers_exact_tail_after_source_files_are_removed(self):
        self.checkpoint()
        self.assertEqual(inspect(self.root)[0]["status"], "awaiting-commit")
        self.commit_first()
        for path in (self.source, self.head, self.tail):
            path.unlink()
        report, directory, _ = inspect(self.root)
        self.assertEqual(report["status"], "ready")
        self.assertEqual((directory / "source.md").read_bytes(), self.raw)
        self.assertEqual((directory / "tail-working.md").read_bytes(), '她接住，朝门口照。\r\n'.encode())

    def test_changed_predecessor_requires_real_check_then_binds_both_versions(self):
        self.checkpoint()
        chapter = self.commit_first("他把灯放在桌上。")
        report, directory, _ = inspect(self.root)
        self.assertEqual(report["status"], "review-required")
        self.assertTrue(report["predecessorChanged"])
        # Local repair preserves the initial recovery snapshot.
        (directory / "tail-working.md").write_text("她从桌上拿起灯，朝门口照。\n")
        result = confirm(self.root, "前章改为把灯放在桌上，尾稿改为从桌上取灯；位置和照明方向一致。")
        self.assertEqual(result["status"], "ready")
        self.assertEqual((directory / "tail.md").read_bytes(), self.tail.read_bytes())
        chapter.write_text("他把灯留在了楼上。\n")
        self.assertEqual(inspect(self.root)[0]["status"], "review-required")
        self.assertEqual(len(inspect(self.root)[2]["checks"]), 1)

    def test_working_tail_edit_invalidates_confirmation(self):
        self.checkpoint()
        self.commit_first()
        report, directory, _ = inspect(self.root)
        (directory / "tail-working.md").write_text("她接住灯，往楼梯走。")
        self.assertEqual(inspect(self.root)[0]["status"], "review-required")
        confirm(self.root, "人物仍在门边，转向楼梯有接续依据。")
        (directory / "tail-working.md").write_text("她已经到了院外。")
        self.assertEqual(inspect(self.root)[0]["status"], "review-required")
        with self.assertRaises(ValueError):
            confirm(self.root, "  ")

    def test_new_commit_does_not_replay_an_older_tail(self):
        self.checkpoint()
        self.commit_first()
        self.set_chapter(2)
        self.assertEqual(inspect(self.root)[0]["status"], "no-checkpoint")
        self.set_chapter(1)  # A rollback can recover its original cut again.
        self.assertEqual(inspect(self.root)[0]["status"], "ready")

    def test_pending_new_slice_takes_precedence_over_previous_tail(self):
        self.checkpoint()
        self.commit_first()
        save(self.root, 2, self.source, self.head, self.tail)
        report, _, _ = inspect(self.root)
        self.assertEqual(report["status"], "awaiting-commit")
        self.assertEqual(report["pendingChapter"], 2)
        with self.assertRaisesRegex(ValueError, "No checkpoint"):
            confirm(self.root, "不能略过已经写出的第二片。")

    def test_snapshot_tampering_and_duplicate_save_do_not_erase_recovery(self):
        directory = Path(self.checkpoint()["checkpoint"])
        with self.assertRaises(FileExistsError):
            self.checkpoint()
        self.assertEqual((directory / "source.md").read_bytes(), self.raw)
        self.commit_first()
        (directory / "tail.md").write_text("改掉原始尾稿")
        with self.assertRaisesRegex(ValueError, "Recovery snapshots changed"):
            inspect(self.root)

    def test_mismatched_slices_and_invalid_anchor_are_rejected_before_writing(self):
        self.tail.write_text("不是原文尾稿")
        with self.assertRaisesRegex(ValueError, "byte for byte"):
            self.checkpoint()
        self.assertFalse((self.root / "drafts").exists())
        with self.assertRaisesRegex(ValueError, "after-chapter"):
            save(self.root, 3, self.source, self.head, self.tail)

    def test_failed_save_removes_only_its_partial_checkpoint(self):
        sibling = self.root / "drafts/continuations/notes.txt"
        sibling.parent.mkdir(parents=True)
        sibling.write_text("keep")
        with patch("draft_checkpoint.write_json_atomic", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.checkpoint()
        self.assertFalse((sibling.parent / "after-0001").exists())
        self.assertEqual(sibling.read_text(), "keep")

    def test_empty_tail_is_explicit(self):
        self.head.write_bytes(self.raw)
        self.tail.write_bytes(b"")
        self.checkpoint()
        self.commit_first(self.raw.decode())
        report, _, _ = inspect(self.root)
        self.assertEqual(report["status"], "ready")
        self.assertTrue(report["emptyTail"])

    def test_real_cut_and_cli_fresh_process_recovery(self):
        text = "他往门口走。\r\n" * 600
        self.source.write_bytes(text.encode())
        point = suggest_cut(text)["cutPoint"]
        self.head.unlink()
        self.tail.unlink()
        export_slices(self.source, self.head, self.tail, text, point["offset"])
        command = [sys.executable, str(SCRIPTS / "draft_checkpoint.py")]
        run = subprocess.run(command + ["save", "--project", str(self.root), "--after-chapter", "1", "--source", str(self.source), "--head", str(self.head), "--tail", str(self.tail)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        chapter = self.commit_first(self.head.read_bytes().decode())
        check = command + ["check", "--project", str(self.root)]
        recovered = subprocess.run(check, capture_output=True, text=True)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        report = json.loads(recovered.stdout)
        self.assertEqual(Path(report["workingTail"]).read_bytes(), self.tail.read_bytes())
        chapter.write_text("他暂时没走。")
        changed = subprocess.run(check, capture_output=True, text=True)
        self.assertEqual(changed.returncode, 1)
        self.assertEqual(json.loads(changed.stdout)["status"], "review-required")


if __name__ == "__main__":
    unittest.main()
