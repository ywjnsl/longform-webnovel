from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from repetition_audit import analyze_paths, project_comparisons


class RepetitionAuditTests(unittest.TestCase):
    def write_chapter(self, root: Path, name: str, body: str) -> Path:
        path = root / name
        path.write_text(f"# 测试\n\n{body}\n", encoding="utf-8")
        return path

    def test_reports_a_long_sentence_repeated_twice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repeated = "然后，她第一次把丈夫的名字，和被调查对象放在了同一页上。"
            chapter = self.write_chapter(root, "第0001章-重复.md", f"{repeated}\n\n她合上卷宗。\n\n{repeated}")
            result = analyze_paths(chapter, [])
            finding = next(item for item in result["findings"] if item["code"] == "exact-sentence-duplicate")
            self.assertEqual(2, len(finding["occurrences"]))
            self.assertEqual({1, 3}, {item["paragraph"] for item in finding["occurrences"]})

    def test_ignores_repeated_short_dialogue(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            chapter = self.write_chapter(Path(temp), "第0001章-短句.md", "“好。”\n\n“好。”")
            self.assertEqual([], analyze_paths(chapter, [])["findings"])

    def test_reports_a_high_similarity_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            body = (
                "她把装着三十年前旧账本的牛皮纸袋推到桌面中央，右手食指始终压着已经起毛的封口，旁边还沾着前一晚没有擦净的墨迹。\n\n"
                "她把装着三十年前旧账本的牛皮纸袋推到桌面中间，右手食指始终压着已经起毛的封口，旁边还沾着前一晚没有擦净的墨迹。"
            )
            chapter = self.write_chapter(Path(temp), "第0001章-近似.md", body)
            codes = {item["code"] for item in analyze_paths(chapter, [])["findings"]}
            self.assertIn("near-sentence-duplicate", codes)

    def test_cli_writes_hash_bound_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chapter = self.write_chapter(root, "第0001章-命令.md", "这是足够长而且只出现一次的测试句子。")
            output = root / "audit.json"
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "repetition_audit.py"), str(chapter), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            expected = hashlib.sha256(chapter.read_bytes()).hexdigest()
            self.assertEqual(expected, result["reviewedTextSha256"])
            self.assertEqual(1, result["chapter"])

    def test_scope_can_include_all_earlier_short_story_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chapters = root / "chapters"
            chapters.mkdir()
            (root / "project.json").write_text(
                json.dumps({"storyMode": "fanqie-short-story"}), encoding="utf-8"
            )
            self.write_chapter(chapters, "第0001章-一.md", "第一节里只有这一句足够长的测试正文。")
            self.write_chapter(chapters, "第0002章-二.md", "第二节里只有这一句足够长的测试正文。")
            third = self.write_chapter(chapters, "第0003章-三.md", "第三节里只有这一句足够长的测试正文。")
            comparisons = project_comparisons(third, root)
            result = analyze_paths(third, comparisons)
            self.assertEqual(
                ["chapters/第0003章-三.md", "chapters/第0001章-一.md", "chapters/第0002章-二.md"],
                result["scopeFiles"],
            )


if __name__ == "__main__":
    unittest.main()
