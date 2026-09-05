from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from validate_project import validate_chapter_reviews  # noqa: E402


class NaturalnessGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "chapters").mkdir()
        (self.root / "reviews").mkdir()
        self.chapter_path = self.root / "chapters" / "第0001章-测试.md"
        self.chapter_text = "第一句已经演出了结果。第二句又替读者总结了一遍。"
        self.chapter_path.write_text(self.chapter_text, encoding="utf-8")
        self.digest = hashlib.sha256(self.chapter_text.encode("utf-8")).hexdigest()
        self.project = {
            "reviewGate": {
                "enforceFromChapter": 1,
                "editorRequired": False,
                "readerRequired": False,
                "lintRequired": False,
                "naturalnessRequired": True,
                "naturalnessEnforceFromChapter": 1,
            }
        }
        self.decisions = {"decisions": []}
        self.review_path = self.root / "reviews" / "第0001章-review.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_review(self, naturalness: dict | None = None) -> None:
        review = {
            "schemaVersion": 1,
            "chapter": 1,
            "reviewedTextSha256": self.digest,
        }
        if naturalness is not None:
            review["naturalness"] = naturalness
        self.review_path.write_text(
            json.dumps(review, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def valid_naturalness(self) -> dict:
        return {
            "status": "pass",
            "diagnosis": "未发现影响沉浸的自然度问题簇。",
            "reviewedTextSha256": self.digest,
            "findings": [],
            "revision": {
                "action": "not-needed",
                "notes": "没有证据支持额外修改。",
            },
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        validate_chapter_reviews(
            self.root,
            self.project,
            {1: self.chapter_path},
            1,
            self.decisions,
            errors,
        )
        return errors

    def test_requires_naturalness_gate_fields(self) -> None:
        del self.project["reviewGate"]["naturalnessRequired"]
        del self.project["reviewGate"]["naturalnessEnforceFromChapter"]

        errors = self.validate()

        self.assertIn("reviewGate.naturalnessRequired must be true", errors)
        self.assertIn(
            "reviewGate.naturalnessEnforceFromChapter must be a positive integer",
            errors,
        )

    def test_rejects_review_without_naturalness_object(self) -> None:
        self.write_review()

        errors = self.validate()

        self.assertIn("Chapter 1 review needs naturalness object", errors)

    def test_accepts_valid_naturalness_review(self) -> None:
        self.write_review(self.valid_naturalness())

        self.assertEqual([], self.validate())

    def test_rejects_disabled_naturalness_gate(self) -> None:
        self.project["reviewGate"]["naturalnessRequired"] = False
        self.write_review()

        self.assertIn("reviewGate.naturalnessRequired must be true", self.validate())

    def test_accepts_resolved_finding_with_verbatim_evidence(self) -> None:
        naturalness = self.valid_naturalness()
        naturalness["status"] = "pass-with-notes"
        naturalness["findings"] = [
            {
                "priority": "medium",
                "category": "over-explanation",
                "evidence": ["第二句又替读者总结了一遍。"],
                "readerCost": "重复结论会压缩读者自行理解的空间。",
                "direction": "保留动作结果，删除重复判断。",
                "resolved": True,
            }
        ]
        self.write_review(naturalness)

        self.assertEqual([], self.validate())

    def test_rejects_naturalness_hash_mismatch(self) -> None:
        naturalness = self.valid_naturalness()
        naturalness["reviewedTextSha256"] = "0" * 64
        self.write_review(naturalness)

        errors = self.validate()

        self.assertIn(
            "Chapter 1 naturalness hash does not match chapter text",
            errors,
        )

    def test_rejects_non_verbatim_evidence(self) -> None:
        naturalness = self.valid_naturalness()
        naturalness["status"] = "pass-with-notes"
        naturalness["findings"] = [
            {
                "priority": "medium",
                "category": "over-explanation",
                "evidence": ["这句话不在正文里。"],
                "readerCost": "读者会被旁白抢先告知结论。",
                "direction": "删除重复判断，保留动作后果。",
                "resolved": True,
            }
        ]
        self.write_review(naturalness)

        errors = self.validate()

        self.assertTrue(
            any(
                "naturalness finding #1 evidence #1 must be copied verbatim"
                in error
                for error in errors
            )
        )

    def test_blocks_unresolved_naturalness_revision(self) -> None:
        naturalness = self.valid_naturalness()
        naturalness["status"] = "needs-revision"
        naturalness["findings"] = [
            {
                "priority": "high",
                "category": "over-explanation",
                "evidence": ["第二句又替读者总结了一遍。"],
                "readerCost": "情绪和判断被旁白提前封口。",
                "direction": "删除总结句，让场景后果停留。",
                "resolved": False,
            }
        ]
        naturalness["revision"] = {
            "action": "not-needed",
            "notes": "尚未处理。",
        }
        self.write_review(naturalness)

        errors = self.validate()

        self.assertIn("Chapter 1 naturalness review still needs revision", errors)
        self.assertIn(
            "Chapter 1 has an unresolved high-priority naturalness finding",
            errors,
        )

    def test_revised_naturalness_requires_before_hash_and_categories(self) -> None:
        naturalness = self.valid_naturalness()
        naturalness["revision"] = {
            "action": "revised",
            "notes": "删除了重复结论，并用动作保留必要信息。",
        }
        self.write_review(naturalness)

        errors = self.validate()

        self.assertIn(
            "Chapter 1 revised naturalness review needs a distinct beforeTextSha256",
            errors,
        )
        self.assertIn(
            "Chapter 1 revised naturalness review needs changedCategories",
            errors,
        )

    def test_accepts_revised_naturalness_with_before_hash_and_categories(self) -> None:
        naturalness = self.valid_naturalness()
        naturalness["revision"] = {
            "action": "revised",
            "beforeTextSha256": "1" * 64,
            "changedCategories": ["over-explanation"],
            "notes": "删除了重复结论，并用动作保留必要信息。",
        }
        self.write_review(naturalness)

        self.assertEqual([], self.validate())

    def test_rejects_current_hash_and_invalid_revised_category(self) -> None:
        naturalness = self.valid_naturalness()
        naturalness["revision"] = {
            "action": "revised",
            "beforeTextSha256": self.digest,
            "changedCategories": ["not-a-category"],
            "notes": "尝试记录一次无效修订。",
        }
        self.write_review(naturalness)

        errors = self.validate()

        self.assertIn(
            "Chapter 1 revised naturalness review needs a distinct beforeTextSha256",
            errors,
        )
        self.assertIn(
            "Chapter 1 revised naturalness review has invalid changed category: not-a-category",
            errors,
        )

    def test_author_approval_requires_confirmed_decision(self) -> None:
        naturalness = self.valid_naturalness()
        naturalness["status"] = "needs-revision"
        naturalness["findings"] = [
            {
                "priority": "high",
                "category": "theme-closure",
                "evidence": ["第二句又替读者总结了一遍。"],
                "readerCost": "结尾余韵被总结句封死。",
                "direction": "停在已经发生的动作后果上。",
                "resolved": False,
            }
        ]
        naturalness["revision"] = {
            "action": "author-approved",
            "decisionId": "keep-ending",
            "notes": "作者明确保留这一收尾方式。",
        }
        self.write_review(naturalness)

        self.assertIn(
            "Chapter 1 naturalness author-approved revision needs a confirmed decisionId",
            self.validate(),
        )

        self.decisions["decisions"] = [{"id": "keep-ending", "status": "confirmed", "kind": "book-title"}]
        self.assertIn(
            "Chapter 1 naturalness author-approved revision needs a confirmed decisionId",
            self.validate(),
        )

        self.decisions["decisions"] = [
            {
                "id": "keep-ending",
                "status": "confirmed",
                "kind": "naturalness-exception",
                "chapter": 1,
                "reviewedTextSha256": self.digest,
            }
        ]
        self.assertEqual([], self.validate())


class NaturalnessProjectLifecycleTests(unittest.TestCase):
    def run_script(self, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / script), *args],
            cwd=SKILL_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def initialize_project(self, root: Path) -> dict:
        result = self.run_script(
            "init_project.py",
            "--path",
            str(root),
            "--title",
            "门禁测试",
            "--style",
            "fanqie-clean",
            "--mode",
            "serial",
            "--protagonist-id",
            "main",
            "--protagonist-name",
            "测试者",
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        return json.loads((root / "project.json").read_text(encoding="utf-8"))

    def test_new_project_enables_naturalness_from_first_chapter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "novel"

            project = self.initialize_project(root)

            self.assertEqual(7, project["schemaVersion"])
            self.assertIs(project["reviewGate"]["naturalnessRequired"], True)
            self.assertEqual(
                1,
                project["reviewGate"]["naturalnessEnforceFromChapter"],
            )

    def test_v6_migration_enforces_naturalness_from_next_chapter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "novel"
            project = self.initialize_project(root)
            project["schemaVersion"] = 6
            project["lastCommittedChapter"] = 3
            project["latestDraftChapter"] = 3
            project["reviewGate"]["naturalnessRequired"] = False
            project["reviewGate"].pop("naturalnessEnforceFromChapter", None)
            (root / "project.json").write_text(
                json.dumps(project, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_script("migrate_project.py", str(root))

            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
            migrated = json.loads((root / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(7, migrated["schemaVersion"])
            self.assertIs(migrated["reviewGate"]["naturalnessRequired"], True)
            self.assertEqual(
                4,
                migrated["reviewGate"]["naturalnessEnforceFromChapter"],
            )


if __name__ == "__main__":
    unittest.main()
