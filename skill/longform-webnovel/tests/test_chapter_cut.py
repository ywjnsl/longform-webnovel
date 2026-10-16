#!/usr/bin/env python3
"""Verify exact prose slicing, shared counting and non-destructive exports."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from chapter_cut import export_slices, suggest_cut
from chapter_metrics import metrics
from webnovel_io import content_char_count


class ChapterCutTests(unittest.TestCase):
    def assert_counted_slice(self, text: str, target: int, **kwargs) -> dict:
        report = suggest_cut(text, target, **kwargs)
        self.assertEqual(report["status"], "ready")
        point = report["cutPoint"]
        head, tail = text[:point["offset"]], text[point["offset"]:]
        self.assertEqual(head + tail, text)
        self.assertEqual(content_char_count(head), point["headChars"])
        self.assertEqual(content_char_count(tail), point["tailChars"])
        self.assertEqual(point["headChars"] + point["tailChars"], content_char_count(text))
        return report

    def test_nearest_sentence_keeps_closing_quote_and_crlf(self):
        text = '# 草稿\r\n\r\n“' + '甲' * 2496 + '。”\r\n\r\n' + '乙' * 40 + '。\r\n'
        point = self.assert_counted_slice(text, 2500)["cutPoint"]
        self.assertTrue(text[:point["offset"]].endswith('。”\r\n\r\n'))
        self.assertEqual(point["headChars"], 2496)

    def test_no_early_cut_and_event_end_residual(self):
        text = '甲。' * 2250
        self.assertEqual(suggest_cut(text)["status"], "continue")
        self.assertEqual(metrics(text, 2500)["lengthSignal"], "continue")
        final = self.assert_counted_slice(text, 2500, final=True)["cutPoint"]
        self.assertEqual(final["offset"], len(text))
        self.assertEqual(final["tailChars"], 0)

    def test_markdown_links_fences_and_ascii_words(self):
        text = '# 忽略标题 123\r\n' + '甲。' * 47 + '[乙。丙](https://example.com/a.b)\r\n'
        text += '```\r\n隐藏。999\r\n\r\n不切这里。\r\n```\r\n'
        text += '型号 pump42 转速 3000。\r\n\r\n' + '丁。' * 100
        point = self.assert_counted_slice(text, 50)["cutPoint"]
        self.assertFalse(text.index('[') < point["offset"] < text.index(')') + 1)
        self.assertFalse(text.index('```') < point["offset"] < text.rindex('```') + 3)

    def test_unfinished_sentence_requires_a_boundary(self):
        text = '甲' * 2700
        self.assertEqual(suggest_cut(text)["status"], "needs-boundary")
        self.assertIsNone(suggest_cut(text)["cutPoint"])
        self.assertEqual(metrics(text, 2500)["lengthAction"], "inspect-boundary")
        self.assertEqual(suggest_cut('')['status'], 'empty')

    def test_link_labels_join_words_without_count_drift(self):
        text = 'the[old](https://example.com)door。' * 2600
        self.assert_counted_slice(text, 2500)

    def test_slice_cannot_turn_inline_hash_into_a_heading(self):
        text = '甲。#乙。丙。'
        report = self.assert_counted_slice(text, 1, window=1)
        self.assertNotEqual(report['cutPoint']['offset'], text.index('#'))

    def test_distant_boundary_is_not_exportable(self):
        text = '甲。' + '乙' * 2999 + '。'
        self.assertEqual(suggest_cut(text)["status"], "needs-boundary")
        with self.assertRaises(ValueError):
            suggest_cut(text, 0)

    def test_paragraph_boundary_without_sentence_punctuation(self):
        text = '甲' * 2498 + '\n\n' + '乙' * 50
        point = self.assert_counted_slice(text, 2500)['cutPoint']
        self.assertEqual(point['boundary'], 'paragraph')
        self.assertEqual(point['headChars'], 2498)

    def test_cli_leaves_outputs_absent_without_a_usable_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, head, tail = [root / name for name in ('draft.md', 'head.md', 'tail.md')]
            source.write_text('甲' * 2700, encoding='utf-8')
            run = subprocess.run(
                [sys.executable, str(SCRIPTS / 'chapter_cut.py'), str(source), '--head', str(head), '--tail', str(tail)],
                capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 1)
            self.assertEqual(json.loads(run.stdout)['status'], 'needs-boundary')
            self.assertFalse(head.exists())
            self.assertFalse(tail.exists())

    def test_repeated_cuts_reassemble_the_exact_draft(self):
        text = '# 连续正文\r\n\r\n' + ('甲乙。\r\n“往下走！”\r\n\r\n' * 1700)
        remainder = text
        slices = []
        while content_char_count(remainder) >= 2500:
            point = self.assert_counted_slice(remainder, 2500)["cutPoint"]
            slices.append(remainder[:point["offset"]])
            remainder = remainder[point["offset"]:]
        slices.append(remainder)
        self.assertGreater(len(slices), 2)
        self.assertEqual(''.join(slices).encode('utf-8'), text.encode('utf-8'))

    def test_cli_export_preserves_bytes_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, head, tail = [root / name for name in ('draft.md', 'head.md', 'tail.md')]
            raw = ('# 草稿\r\n\r\n' + '甲乙。\r\n' * 1400).encode('utf-8')
            source.write_bytes(raw)
            cmd = [sys.executable, str(SCRIPTS / 'chapter_cut.py'), str(source), '--head', str(head), '--tail', str(tail)]
            run = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)['status'], 'ready')
            self.assertEqual(head.read_bytes() + tail.read_bytes(), raw)
            before = head.read_bytes(), tail.read_bytes()
            retry = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(retry.returncode, 0)
            self.assertEqual((head.read_bytes(), tail.read_bytes()), before)
            self.assertEqual(source.read_bytes(), raw)

    def test_export_rolls_back_only_its_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, head, blocker = [root / name for name in ('source', 'head', 'blocker')]
            source.write_bytes(b'original')
            blocker.write_bytes(b'keep')
            with self.assertRaises(OSError):
                export_slices(source, head, blocker / 'tail', '甲。乙。', 2)
            self.assertFalse(head.exists())
            self.assertEqual(blocker.read_bytes(), b'keep')
            self.assertEqual(source.read_bytes(), b'original')
            with self.assertRaises(ValueError):
                export_slices(source, source, root / 'tail', '甲。乙。', 2)


if __name__ == '__main__':
    unittest.main()
