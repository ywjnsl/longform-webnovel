# Naturalness Gate v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `longform-webnovel` with deterministic duplicate detection, evidence-based modifier and rhetorical-pattern review, and optional Zhuque passage feedback without optimizing for detector evasion.

**Architecture:** Add a dependency-free `repetition_audit.py` that produces a hash-bound report for the current chapter while comparing earlier chapters. Extend the existing prose lint and review validator rather than creating a second naturalness system; project schema v8 makes the repetition report mandatory from the first new chapter after migration. Keep Zhuque evidence optional and non-blocking, while every surviving deterministic repetition candidate requires an explicit, hash-bound disposition.

**Tech Stack:** Python 3.11+ standard library, `unittest`, JSON reports, Markdown skill references.

---

## File Map

- Create `skill/longform-webnovel/scripts/repetition_audit.py`: visible-text unit extraction, exact/near duplicate comparison, JSON CLI.
- Create `skill/longform-webnovel/tests/test_repetition_audit.py`: focused unit and CLI tests.
- Modify `skill/longform-webnovel/scripts/webnovel_io.py`: project schema v8.
- Modify `skill/longform-webnovel/scripts/init_project.py`: enable repetition reports for new projects.
- Modify `skill/longform-webnovel/scripts/migrate_project.py`: migrate v7 and older projects without retroactively blocking old chapters.
- Modify `skill/longform-webnovel/scripts/validate_project.py`: validate repetition reports, dispositions, and optional Zhuque evidence.
- Modify `skill/longform-webnovel/scripts/prose_lint.py`: modifier clusters, rhetorical symmetry, cadence packaging, richer baseline metrics.
- Modify `skill/longform-webnovel/tests/test_naturalness_gate.py`: schema, repetition-gate, and Zhuque validation tests.
- Modify `tests/test_longform_webnovel.py`: integration coverage for new scripts and schema v8.
- Modify `tests/check_skill.py`: package-structure assertion for the new script.
- Modify `skill/longform-webnovel/SKILL.md`: mandatory execution and routing.
- Modify `skill/longform-webnovel/references/prose-naturalization.md`: scene-triggered naturalization techniques and anti-formula boundaries.
- Modify `skill/longform-webnovel/references/webnovel-naturalness-review.md`: new evidence categories and disposition contract.
- Modify `skill/longform-webnovel/references/review-system.md`: command order, report schemas, and blocking rules.
- Modify `skill/longform-webnovel/references/operations.md`: staging and hash invalidation rules.
- Modify `README.md`: user-facing capability and test command.

### Task 0: Make the Integration Harness Use the Active Python

**Files:**
- Modify: `tests/test_longform_webnovel.py`

- [ ] **Step 1: Reproduce the Windows launcher failure**

Run: `python tests/test_longform_webnovel.py`

Expected on the current machine: FAIL when the harness tries to start the inaccessible Windows Store `python3.exe` alias. This is a test-runner failure, not a product failure.

- [ ] **Step 2: Replace subprocess launcher literals**

The file already imports `sys`. Replace every subprocess argument equal to the string literal `"python3"` with `sys.executable`; do not change shebangs, README commands, or production scripts. Representative calls become:

```python
run(sys.executable, str(SCRIPTS / "init_project.py"), "--path", str(path), "--title", title, "--style", "fanqie-clean")
args = [sys.executable, str(SCRIPTS / "commit_chapter.py"), "--project", str(project), "--staging", str(stage)]
```

- [ ] **Step 3: Verify the existing suite can execute**

Run: `python tests/test_longform_webnovel.py`

Expected: the suite reaches its existing success message without a `python3.exe` launcher error.

- [ ] **Step 4: Commit the harness portability fix**

```powershell
git add tests/test_longform_webnovel.py
git commit -m "test: use active Python interpreter"
```

### Task 1: Deterministic Repetition Audit

**Files:**
- Create: `skill/longform-webnovel/tests/test_repetition_audit.py`
- Create: `skill/longform-webnovel/scripts/repetition_audit.py`

- [ ] **Step 1: Write tests for the missed duplicate and legitimate counterexamples**

Create tests that import `analyze_paths` and assert the public JSON shape:

```python
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
            (root / "project.json").write_text(json.dumps({"storyMode": "fanqie-short-story"}), encoding="utf-8")
            first = self.write_chapter(chapters, "第0001章-一.md", "第一节里只有这一句足够长的测试正文。")
            second = self.write_chapter(chapters, "第0002章-二.md", "第二节里只有这一句足够长的测试正文。")
            third = self.write_chapter(chapters, "第0003章-三.md", "第三节里只有这一句足够长的测试正文。")
            comparisons = project_comparisons(third, root)
            result = analyze_paths(third, comparisons)
            self.assertEqual(
                ["chapters/第0003章-三.md", "chapters/第0001章-一.md", "chapters/第0002章-二.md"],
                result["scopeFiles"],
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python skill/longform-webnovel/tests/test_repetition_audit.py`

Expected: FAIL with `ModuleNotFoundError: No module named 'repetition_audit'`.

- [ ] **Step 3: Implement visible-unit extraction and exact/near comparison**

Create `repetition_audit.py` with these public contracts:

```python
#!/usr/bin/env python3
"""Find exact and high-similarity sentence repetition in Chinese fiction."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from webnovel_io import load_json, story_mode, write_json_atomic

CHAPTER_RE = re.compile(r"^第(\d{4,})章-.+\.md$")
UNIT_RE = re.compile(r"[^。！？!?]+[。！？!?]?")
CONTENT_RE = re.compile(r"[A-Za-z0-9\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
NORMALIZE_RE = re.compile(r"[^A-Za-z0-9\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
EXACT_MIN_CHARS = 14
NEAR_MIN_CHARS = 18
DEFAULT_NEAR_THRESHOLD = 0.82


def normalize(text: str) -> str:
    return NORMALIZE_RE.sub("", text).lower()


def visible_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    in_fence = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped or stripped.startswith("#"):
            continue
        paragraphs.append(re.sub(r"!?(?:\[([^]]*)\])\([^)]*\)", r"\1", stripped))
    return paragraphs


def units(path: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for paragraph_number, paragraph in enumerate(visible_paragraphs(path.read_text(encoding="utf-8")), 1):
        sentence_number = 0
        for match in UNIT_RE.finditer(paragraph):
            text = match.group(0).strip()
            normalized = normalize(text)
            if not normalized:
                continue
            sentence_number += 1
            result.append({
                "file": f"chapters/{path.name}",
                "paragraph": paragraph_number,
                "sentence": sentence_number,
                "text": text,
                "normalized": normalized,
                "contentChars": len(CONTENT_RE.findall(text)),
            })
    return result


def shingles(value: str, size: int = 3) -> set[str]:
    if len(value) <= size:
        return {value}
    return {value[index:index + size] for index in range(len(value) - size + 1)}


def jaccard(left: str, right: str) -> float:
    left_set = shingles(left)
    right_set = shingles(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 0.0


def finding_id(code: str, occurrences: list[dict[str, object]]) -> str:
    identity = [(item["file"], item["paragraph"], item["sentence"], item["normalized"]) for item in occurrences]
    payload = json.dumps([code, identity], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def public_occurrence(item: dict[str, object]) -> dict[str, object]:
    return {key: item[key] for key in ("file", "paragraph", "sentence", "text")}


def analyze_paths(primary: Path, comparisons: list[Path], near_threshold: float = DEFAULT_NEAR_THRESHOLD) -> dict:
    primary = primary.resolve()
    paths = [primary]
    for comparison in comparisons:
        resolved = comparison.resolve()
        if resolved not in paths:
            paths.append(resolved)
    all_units = [item for path in paths for item in units(path)]
    primary_file = f"chapters/{primary.name}"
    findings: list[dict[str, object]] = []
    exact_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in all_units:
        if item["contentChars"] >= EXACT_MIN_CHARS:
            exact_groups[str(item["normalized"])].append(item)
    exact_keys: set[str] = set()
    for normalized, group in exact_groups.items():
        if len(group) < 2 or not any(item["file"] == primary_file for item in group):
            continue
        exact_keys.add(normalized)
        occurrences = [public_occurrence(item) for item in group]
        findings.append({
            "id": finding_id("exact-sentence-duplicate", group),
            "code": "exact-sentence-duplicate",
            "severity": "block",
            "similarity": 1.0,
            "occurrences": occurrences,
        })
    eligible = [item for item in all_units if item["contentChars"] >= NEAR_MIN_CHARS]
    for index, left in enumerate(eligible):
        for right in eligible[index + 1:]:
            if left["normalized"] == right["normalized"]:
                continue
            if primary_file not in {left["file"], right["file"]}:
                continue
            similarity = jaccard(str(left["normalized"]), str(right["normalized"]))
            if similarity < near_threshold:
                continue
            pair = [left, right]
            findings.append({
                "id": finding_id("near-sentence-duplicate", pair),
                "code": "near-sentence-duplicate",
                "severity": "review",
                "similarity": round(similarity, 3),
                "occurrences": [public_occurrence(item) for item in pair],
            })
    findings.sort(key=lambda item: (item["code"], item["id"]))
    chapter_match = CHAPTER_RE.match(primary.name)
    return {
        "schemaVersion": 1,
        "chapter": int(chapter_match.group(1)) if chapter_match else None,
        "reviewedTextSha256": hashlib.sha256(primary.read_bytes()).hexdigest(),
        "claim": "editorial-repetition-signals-not-authorship-detection",
        "scopeFiles": [f"chapters/{path.name}" for path in paths],
        "thresholds": {"exactMinChars": EXACT_MIN_CHARS, "nearMinChars": NEAR_MIN_CHARS, "nearJaccard": near_threshold},
        "status": "review" if findings else "pass",
        "findings": findings,
    }


def project_comparisons(primary: Path, project_root: Path) -> list[Path]:
    match = CHAPTER_RE.match(primary.name)
    if match is None:
        return []
    current = int(match.group(1))
    candidates: list[tuple[int, Path]] = []
    for path in (project_root / "chapters").glob("第*章-*.md"):
        candidate_match = CHAPTER_RE.match(path.name)
        if candidate_match and int(candidate_match.group(1)) < current:
            candidates.append((int(candidate_match.group(1)), path))
    candidates.sort(key=lambda item: item[0])
    paths = [path for _, path in candidates]
    project = load_json(project_root / "project.json")
    return paths if story_mode(project) == "fanqie-short-story" else paths[-5:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapter", type=Path)
    parser.add_argument("--compare", action="append", default=[], type=Path)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--near-threshold", type=float, default=DEFAULT_NEAR_THRESHOLD)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0.0 < args.near_threshold <= 1.0:
        raise SystemExit("--near-threshold must be greater than 0 and at most 1")
    comparisons = [*args.compare]
    if args.project:
        comparisons.extend(project_comparisons(args.chapter, args.project.resolve()))
    result = analyze_paths(args.chapter, comparisons, args.near_threshold)
    if args.output:
        write_json_atomic(args.output.resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python skill/longform-webnovel/tests/test_repetition_audit.py`

Expected: `Ran 5 tests` and `OK`.

- [ ] **Step 5: Commit the isolated audit**

```powershell
git add skill/longform-webnovel/scripts/repetition_audit.py skill/longform-webnovel/tests/test_repetition_audit.py
git commit -m "feat: add deterministic repetition audit"
```

### Task 2: Project Schema v8 and Repetition Gate

**Files:**
- Modify: `skill/longform-webnovel/scripts/webnovel_io.py`
- Modify: `skill/longform-webnovel/scripts/init_project.py`
- Modify: `skill/longform-webnovel/scripts/migrate_project.py`
- Modify: `skill/longform-webnovel/scripts/validate_project.py`
- Modify: `skill/longform-webnovel/tests/test_naturalness_gate.py`
- Modify: `tests/test_longform_webnovel.py`

- [ ] **Step 1: Add failing schema and gate tests**

Add tests asserting:

```python
def test_new_project_enables_repetition_gate_from_first_chapter(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir) / "novel"
        project = self.initialize_project(root)
        self.assertEqual(8, project["schemaVersion"])
        self.assertIs(project["reviewGate"]["repetitionRequired"], True)
        self.assertEqual(1, project["reviewGate"]["repetitionEnforceFromChapter"])

def test_v7_migration_enforces_repetition_from_next_chapter(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir) / "novel"
        project = self.initialize_project(root)
        project["schemaVersion"] = 7
        project["lastCommittedChapter"] = 3
        project["latestDraftChapter"] = 3
        project["reviewGate"].pop("repetitionRequired", None)
        project["reviewGate"].pop("repetitionEnforceFromChapter", None)
        (root / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = self.run_script("migrate_project.py", str(root))
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        migrated = json.loads((root / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(8, migrated["schemaVersion"])
        self.assertIs(migrated["reviewGate"]["repetitionRequired"], True)
        self.assertEqual(4, migrated["reviewGate"]["repetitionEnforceFromChapter"])
```

Add a validator test whose repetition report contains one exact finding and no disposition; assert the error contains `needs a repetition disposition`. Add the same report with this object under `naturalness` and assert validation passes:

```python
"repetitionExceptions": [{
    "findingId": finding_id,
    "reason": "人物在质询中逐字要求证人确认原话。",
    "reviewedTextSha256": self.digest,
}]
```

Update `NaturalnessGateTests.setUp` with `repetitionRequired: True` and `repetitionEnforceFromChapter: 1`. Add this helper and call it from `setUp` so unrelated naturalness tests keep a valid deterministic report:

```python
def write_repetition_report(self, findings: list[dict] | None = None) -> None:
    self.repetition_path = self.root / "reviews" / "第0001章-repetition.json"
    self.repetition_path.write_text(json.dumps({
        "schemaVersion": 1,
        "chapter": 1,
        "reviewedTextSha256": self.digest,
        "claim": "editorial-repetition-signals-not-authorship-detection",
        "scopeFiles": [f"chapters/{self.chapter_path.name}"],
        "thresholds": {"exactMinChars": 14, "nearMinChars": 18, "nearJaccard": 0.82},
        "status": "review" if findings else "pass",
        "findings": findings or [],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 2: Run the lifecycle tests and verify RED**

Run: `python skill/longform-webnovel/tests/test_naturalness_gate.py`

Expected: FAIL because schema remains 7 and no repetition gate is validated.

- [ ] **Step 3: Bump schema and initialize/migrate gate fields**

Make these exact changes:

```python
# webnovel_io.py
CURRENT_PROJECT_SCHEMA = 8

# init_project.py reviewGate
"repetitionRequired": True,
"repetitionEnforceFromChapter": 1,

# migrate_project.py
review_gate["repetitionRequired"] = True
if old_version < 8:
    review_gate["repetitionEnforceFromChapter"] = committed + 1 if committed else 1
else:
    review_gate.setdefault("repetitionEnforceFromChapter", 1)
```

Update existing schema assertions in both test files from 7 to 8. Preserve the v6 naturalness migration test; it must now assert both naturalness and repetition begin at `committed + 1`.

- [ ] **Step 4: Implement report and disposition validation**

Add constants and a focused helper in `validate_project.py`:

```python
VALID_REPETITION_CODE = {"exact-sentence-duplicate", "near-sentence-duplicate"}


def validate_repetition_report(
    root: Path,
    chapter: int,
    chapter_path: Path,
    digest: str,
    naturalness: dict,
    required_scope: set[str],
    errors: list[str],
) -> None:
    path = root / "reviews" / f"第{chapter:04d}章-repetition.json"
    if not path.is_file():
        errors.append(f"Chapter {chapter} needs reviews/{path.name}")
        return
    report = load_json(path, errors)
    if report.get("schemaVersion") != 1:
        errors.append(f"Chapter {chapter} repetition schemaVersion must be 1")
    if report.get("chapter") != chapter:
        errors.append(f"Chapter {chapter} repetition chapter number does not match")
    if report.get("reviewedTextSha256") != digest:
        errors.append(f"Chapter {chapter} repetition hash does not match chapter text")
    if report.get("claim") != "editorial-repetition-signals-not-authorship-detection":
        errors.append(f"Chapter {chapter} repetition report has invalid claim")
    scope = report.get("scopeFiles")
    if not isinstance(scope, list) or any(not isinstance(item, str) for item in scope):
        errors.append(f"Chapter {chapter} repetition scopeFiles must be a string array")
        scope_set: set[str] = set()
    else:
        scope_set = set(scope)
    for missing in sorted(required_scope - scope_set):
        errors.append(f"Chapter {chapter} repetition scope is missing {missing}")
    findings = report.get("findings")
    if not isinstance(findings, list):
        errors.append(f"Chapter {chapter} repetition findings must be an array")
        return
    dispositions = naturalness.get("repetitionExceptions", []) if isinstance(naturalness, dict) else []
    if not isinstance(dispositions, list):
        errors.append(f"Chapter {chapter} repetitionExceptions must be an array")
        dispositions = []
    approved: set[str] = set()
    for index, item in enumerate(dispositions):
        label = f"Chapter {chapter} repetition exception #{index + 1}"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        if not is_concrete(item.get("findingId")) or not is_concrete(item.get("reason")):
            errors.append(f"{label} needs findingId and concrete reason")
        if item.get("reviewedTextSha256") != digest:
            errors.append(f"{label} hash does not match chapter text")
        if isinstance(item.get("findingId"), str):
            approved.add(item["findingId"])
    seen: set[str] = set()
    for index, finding in enumerate(findings):
        label = f"Chapter {chapter} repetition finding #{index + 1}"
        if not isinstance(finding, dict):
            errors.append(f"{label} must be an object")
            continue
        finding_id = finding.get("id")
        if not is_concrete(finding_id) or finding_id in seen:
            errors.append(f"{label} needs a unique id")
            continue
        seen.add(finding_id)
        if finding.get("code") not in VALID_REPETITION_CODE:
            errors.append(f"{label} has invalid code")
        occurrences = finding.get("occurrences")
        if not isinstance(occurrences, list) or len(occurrences) < 2:
            errors.append(f"{label} needs at least two occurrences")
        else:
            includes_current = False
            for occurrence_index, occurrence in enumerate(occurrences):
                occurrence_label = f"{label} occurrence #{occurrence_index + 1}"
                if not isinstance(occurrence, dict) or not is_concrete(occurrence.get("text")):
                    errors.append(f"{occurrence_label} needs verbatim text")
                    continue
                relative_text = occurrence.get("file")
                if not isinstance(relative_text, str):
                    errors.append(f"{occurrence_label} needs a chapter file")
                    continue
                relative = Path(relative_text)
                if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 2 or relative.parts[0] != "chapters":
                    errors.append(f"{occurrence_label} file must be inside chapters")
                    continue
                source = root / relative
                if not source.is_file():
                    errors.append(f"{occurrence_label} chapter file is missing")
                    continue
                if occurrence["text"] not in source.read_text(encoding="utf-8"):
                    errors.append(f"{occurrence_label} text is not in its chapter file")
                if source.resolve() == chapter_path.resolve():
                    includes_current = True
                for field in ("paragraph", "sentence"):
                    value = occurrence.get(field)
                    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                        errors.append(f"{occurrence_label} {field} must be a positive integer")
            if not includes_current:
                errors.append(f"{label} must include the current chapter")
        if finding_id not in approved:
            errors.append(f"{label} needs a repetition disposition")
    unknown = approved - seen
    for finding_id in sorted(unknown):
        errors.append(f"Chapter {chapter} repetition exception references unknown finding: {finding_id}")
```

Validate `reviewGate.repetitionRequired` as `true` and `reviewGate.repetitionEnforceFromChapter` as a positive integer beside the existing naturalness gate fields. Add a `mode: str` parameter to `validate_naturalness_reviews` and pass `story_mode(project)` from `validate_chapter_reviews`. Build the required scope from committed chapter files: all earlier sections for `fanqie-short-story`, the preceding five chapters for `serial`, plus the current chapter. Call the helper only when the repetition gate is enabled and `chapter >= repetitionEnforceFromChapter`:

```python
if gate.get("repetitionRequired") is True and chapter >= gate["repetitionEnforceFromChapter"]:
    earlier = sorted((number, path) for number, path in chapter_files.items() if number < chapter)
    compared = earlier if mode == "fanqie-short-story" else earlier[-5:]
    required_scope = {f"chapters/{chapter_path.name}"} | {f"chapters/{path.name}" for _, path in compared}
    validate_repetition_report(root, chapter, chapter_path, digest, naturalness, required_scope, errors)
```

Update `prepare_stage` in `tests/test_longform_webnovel.py` so every staged chapter writes a valid empty repetition report by default:

```python
previous = sorted(
    (int(match.group(1)), path)
    for path in (project_root / "chapters").glob("第*章-*.md")
    if (match := re.match(r"^第(\d{4,})章-.+\.md$", path.name)) and int(match.group(1)) < chapter
)
compared = previous if read_json(project_root / "project.json").get("storyMode") == "fanqie-short-story" else previous[-5:]
write_json(stage / "reviews" / f"第{chapter:04d}章-repetition.json", {
    "schemaVersion": 1,
    "chapter": chapter,
    "reviewedTextSha256": digest,
    "claim": "editorial-repetition-signals-not-authorship-detection",
    "scopeFiles": [f"chapters/{chapter_path.name}", *(f"chapters/{path.name}" for _, path in compared)],
    "thresholds": {"exactMinChars": 14, "nearMinChars": 18, "nearJaccard": 0.82},
    "status": "pass",
    "findings": [],
})
```

- [ ] **Step 5: Run focused and integration tests**

Run:

```powershell
python skill/longform-webnovel/tests/test_naturalness_gate.py
python tests/test_longform_webnovel.py
```

Expected: both commands end in `OK` or the integration script's success message.

- [ ] **Step 6: Commit the schema and gate**

```powershell
git add skill/longform-webnovel/scripts/webnovel_io.py skill/longform-webnovel/scripts/init_project.py skill/longform-webnovel/scripts/migrate_project.py skill/longform-webnovel/scripts/validate_project.py skill/longform-webnovel/tests/test_naturalness_gate.py tests/test_longform_webnovel.py
git commit -m "feat: enforce repetition reports in schema v8"
```

### Task 3: Modifier, Rhetorical Symmetry, and Cadence Signals

**Files:**
- Modify: `skill/longform-webnovel/scripts/prose_lint.py`
- Modify: `tests/test_longform_webnovel.py`

- [ ] **Step 1: Add failing behavior tests**

Extend `test_prose_lint` with separate fixtures and assertions:

```python
single_modifier = base / "第0002章-单个副词.md"
single_modifier.write_text("# 第二章\n\n她忽然停住，听见楼下有人叫她。\n", encoding="utf-8")
single_codes = {item["code"] for item in json.loads(run("python", str(SCRIPTS / "prose_lint.py"), str(single_modifier)).stdout)["findings"]}
assert "modifier-cluster" not in single_codes

modifier_cluster = base / "第0003章-副词簇.md"
modifier_cluster.write_text("# 第三章\n\n她忽然回头，微微皱眉。她轻轻关门，又缓缓坐下。她默默低头，终于开口。\n", encoding="utf-8")
cluster_codes = {item["code"] for item in json.loads(run("python", str(SCRIPTS / "prose_lint.py"), str(modifier_cluster)).stdout)["findings"]}
assert "modifier-cluster" in cluster_codes

symmetry = base / "第0004章-工整句.md"
symmetry.write_text("# 第四章\n\n合同在，镯子在。人情归人情，生意归生意。两张纸。两个签名。\n", encoding="utf-8")
symmetry_codes = {item["code"] for item in json.loads(run("python", str(SCRIPTS / "prose_lint.py"), str(symmetry)).stdout)["findings"]}
assert "rhetorical-symmetry" in symmetry_codes

cadence = base / "第0005章-包装节拍.md"
cadence.write_text(
    "# 第五章\n\n他抬眼。\n“你说谎。”\n这意味着她已经输了。\n"
    "她合上文件。\n“证据呢？”\n这说明他根本没有准备好。\n",
    encoding="utf-8",
)
cadence_codes = {item["code"] for item in json.loads(run("python", str(SCRIPTS / "prose_lint.py"), str(cadence)).stdout)["findings"]}
assert "cadence-packaging" in cadence_codes

baseline_paths = []
for index in range(3):
    path = base / f"第{index + 10:04d}章-人工基线.md"
    path.write_text("# 基线\n\n“账对了吗？”她问。\n“还差多少？”他没抬头。\n", encoding="utf-8")
    baseline_paths.extend(("--baseline", str(path)))
drift_result = json.loads(run("python", str(SCRIPTS / "prose_lint.py"), str(modifier_cluster), *baseline_paths).stdout)
drift_codes = {item["code"] for item in drift_result["findings"]}
assert "baseline-drift-modifierRatePer1k" in drift_codes
```

- [ ] **Step 2: Run the integration test and verify RED**

Run: `python tests/test_longform_webnovel.py`

Expected: FAIL because `modifier-cluster` and `rhetorical-symmetry` are absent.

- [ ] **Step 3: Add the smallest evidence-producing detectors**

Add constants and helpers:

```python
MODIFIER_MARKERS = ("其实", "显然", "忽然", "突然", "缓缓", "轻轻", "微微", "默默", "下意识地", "终于", "只是", "竟然")
SYMMETRY_PATTERNS = (
    re.compile(r"[\u3400-\u9fff]{1,8}在[，,、][\u3400-\u9fff]{1,8}在"),
    re.compile(r"([\u3400-\u9fff]{1,8})归\1[，,、]([\u3400-\u9fff]{1,8})归\2"),
    re.compile(r"[一二两三四五六七八九十][\u3400-\u9fff]{1,6}[。！？][一二两三四五六七八九十][\u3400-\u9fff]{1,6}[。！？]"),
)


def modifier_clusters(text: str) -> list[str]:
    sentences = [item.strip() for item in SENTENCE_SPLIT_RE.split(strip_markdown(text)) if item.strip()]
    evidence: list[str] = []
    for index in range(max(0, len(sentences) - 2)):
        window = sentences[index:index + 3]
        joined = "。".join(window)
        hits = [marker for marker in MODIFIER_MARKERS for _ in range(joined.count(marker))]
        if len(hits) >= 5 and len(set(hits)) >= 3:
            evidence.append(joined)
    return list(dict.fromkeys(evidence))[:3]


def rhetorical_symmetry(text: str) -> list[str]:
    body = strip_markdown(text)
    matches = [match.group(0) for pattern in SYMMETRY_PATTERNS for match in pattern.finditer(body)]
    unique = list(dict.fromkeys(matches))
    return unique[:4] if len(unique) >= 2 else []


def cadence_packages(text: str) -> list[str]:
    lines = [line.strip() for line in strip_markdown(text).splitlines() if line.strip()]
    candidates: list[str] = []
    conclusion_markers = (*EXPLANATION_MARKERS, "这说明", "所以", "原来")
    for index in range(len(lines) - 2):
        action, dialogue, conclusion = lines[index:index + 3]
        if (
            0 < content_char_count(action) <= 8
            and DIALOGUE_RE.search(dialogue)
            and any(marker in conclusion for marker in conclusion_markers)
        ):
            candidates.append(" / ".join((action, dialogue, conclusion)))
    return candidates[:3] if len(candidates) >= 2 else []
```

In `analyze`, append `review` findings only when evidence exists. Emit codes `modifier-cluster`, `rhetorical-symmetry`, and `cadence-packaging`. Messages must say to inspect whether the modifiers, symmetry, or three-beat packages replace character-specific action or repeat a deliberate cadence; they must not instruct blanket deletion.

- [ ] **Step 4: Extend baseline metrics without creating a score**

Add a linear-interpolation quantile helper:

Use this implementation:

```python
def quantile(values: list[int], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
```

In `text_metrics`, calculate and return the new fields with these expressions:

```python
question_count = body.count("？") + body.count("?")
modifier_count = sum(body.count(marker) for marker in MODIFIER_MARKERS)
sentence_count = len(sentence_lengths)
unit = max(total / 1000, 1.0)

"sentenceLengthP25": round(quantile(sentence_lengths, 0.25), 2),
"sentenceLengthP50": round(quantile(sentence_lengths, 0.50), 2),
"sentenceLengthP75": round(quantile(sentence_lengths, 0.75), 2),
"questionRatio": round(question_count / sentence_count, 3) if sentence_count else 0.0,
"modifierRatePer1k": round(modifier_count / unit, 3),
```

Add the five keys to the baseline aggregate. Only when at least three baseline files are supplied, append these review-only drift findings:

```python
for key, label, threshold in (
    ("questionRatio", "question ratio", 0.18),
    ("modifierRatePer1k", "modifier rate per 1,000 characters", 3.0),
):
    actual = metrics[key]
    expected = baseline[key]
    if abs(actual - expected) > threshold:
        findings.append({
            "code": f"baseline-drift-{key}",
            "severity": "review",
            "count": 1,
            "evidence": [],
            "message": f"Draft {label} ({actual}) differs from the approved-project baseline ({expected}); inspect the cause rather than optimizing the number.",
        })
```

- [ ] **Step 5: Run focused integration coverage and commit**

Run: `python tests/test_longform_webnovel.py`

Expected: integration suite succeeds and the single-modifier fixture remains unflagged.

```powershell
git add skill/longform-webnovel/scripts/prose_lint.py tests/test_longform_webnovel.py
git commit -m "feat: add evidence-based naturalness lint signals"
```

### Task 4: Optional Zhuque Passage Evidence

**Files:**
- Modify: `skill/longform-webnovel/scripts/validate_project.py`
- Modify: `skill/longform-webnovel/tests/test_naturalness_gate.py`

- [ ] **Step 1: Add failing tests for valid, stale, and missing-artifact feedback**

Add a helper that places this object beside `naturalness` in the review JSON:

```python
{
    "provider": "zhuque",
    "checkedAt": "2026-09-06T10:00:00+08:00",
    "reviewedTextSha256": self.digest,
    "overallSignal": "逐段报告已提供",
    "sourceArtifacts": ["reviews/evidence/朱雀-第0001章.png"],
    "flaggedPassages": [{
        "text": "第二句又替读者总结了一遍。",
        "location": {"paragraph": 1},
        "externalLabel": "疑似 AI 生成",
        "editorDiagnosis": "over-explanation",
        "action": "revised",
        "resolved": True,
    }],
}
```

Create the evidence file for the valid test and assert no warnings. In two separate tests, use a stale hash and a missing artifact; assert warnings contain `externalNaturalness hash does not match` and `externalNaturalness artifact is missing`. Confirm neither case adds a repetition-gate error.

- [ ] **Step 2: Run the naturalness tests and verify RED**

Run: `python skill/longform-webnovel/tests/test_naturalness_gate.py`

Expected: FAIL because no external feedback validator exists.

- [ ] **Step 3: Implement a warning-only validator**

Add this helper to `validate_project.py`:

```python
VALID_EXTERNAL_ACTION = {"kept", "revised", "rejected"}


def validate_external_naturalness(
    root: Path,
    chapter: int,
    chapter_text: str,
    digest: str,
    value: object,
    warnings: list[str],
) -> None:
    if value is None:
        return
    prefix = f"Chapter {chapter} externalNaturalness"
    if not isinstance(value, dict):
        warnings.append(f"{prefix} must be an object")
        return
    if value.get("provider") != "zhuque":
        warnings.append(f"{prefix} provider must be zhuque")
    if not is_concrete(value.get("checkedAt")):
        warnings.append(f"{prefix} needs checkedAt")
    if value.get("reviewedTextSha256") != digest:
        warnings.append(f"{prefix} hash does not match chapter text")
    if not is_concrete(value.get("overallSignal")):
        warnings.append(f"{prefix} needs the original overallSignal")
    artifacts = value.get("sourceArtifacts")
    if not isinstance(artifacts, list):
        warnings.append(f"{prefix} sourceArtifacts must be an array")
        artifacts = []
    for index, artifact in enumerate(artifacts):
        label = f"{prefix} artifact #{index + 1}"
        if not isinstance(artifact, str) or not artifact.strip():
            warnings.append(f"{label} must be a non-empty relative path")
            continue
        relative = Path(artifact)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or len(relative.parts) < 3
            or relative.parts[:2] != ("reviews", "evidence")
        ):
            warnings.append(f"{label} must be inside reviews/evidence")
            continue
        if not (root / relative).is_file():
            warnings.append(f"{prefix} artifact is missing: {artifact}")
    passages = value.get("flaggedPassages")
    if not isinstance(passages, list):
        warnings.append(f"{prefix} flaggedPassages must be an array")
        return
    for index, passage in enumerate(passages):
        label = f"{prefix} passage #{index + 1}"
        if not isinstance(passage, dict):
            warnings.append(f"{label} must be an object")
            continue
        text = passage.get("text")
        if not is_concrete(text) or text not in chapter_text:
            warnings.append(f"{label} text must be copied verbatim from chapter text")
        location = passage.get("location")
        paragraph = location.get("paragraph") if isinstance(location, dict) else None
        if not isinstance(paragraph, int) or isinstance(paragraph, bool) or paragraph <= 0:
            warnings.append(f"{label} paragraph must be a positive integer")
        if not is_concrete(passage.get("externalLabel")):
            warnings.append(f"{label} needs the original externalLabel")
        if passage.get("editorDiagnosis") not in VALID_NATURALNESS_CATEGORY:
            warnings.append(f"{label} has invalid editorDiagnosis")
        if passage.get("action") not in VALID_EXTERNAL_ACTION:
            warnings.append(f"{label} has invalid action")
        if not isinstance(passage.get("resolved"), bool):
            warnings.append(f"{label} resolved must be boolean")
```

Thread warnings without breaking existing direct callers:

```python
def validate_chapter_reviews(
    root: Path,
    project: dict,
    chapter_files: dict[int, Path],
    committed: object,
    decision_doc: dict,
    errors: list[str],
    warnings: list[str] | None = None,
) -> None:
    warnings = [] if warnings is None else warnings
```

Add `warnings` to `validate_naturalness_reviews`, call `validate_external_naturalness` with `review.get("externalNaturalness")`, and pass the project-level warnings list from `validate_project`. Keep every malformed or stale external field warning-only so it cannot bypass or replace the deterministic repetition gate.

- [ ] **Step 4: Run tests and commit**

Run:

```powershell
python skill/longform-webnovel/tests/test_naturalness_gate.py
python tests/test_longform_webnovel.py
```

Expected: both suites succeed; stale Zhuque evidence produces a warning but does not bypass repetition validation.

```powershell
git add skill/longform-webnovel/scripts/validate_project.py skill/longform-webnovel/tests/test_naturalness_gate.py
git commit -m "feat: validate optional Zhuque passage feedback"
```

### Task 5: Skill Instructions and Behavioral Coverage

**Files:**
- Modify: `skill/longform-webnovel/SKILL.md`
- Modify: `skill/longform-webnovel/references/prose-naturalization.md`
- Modify: `skill/longform-webnovel/references/webnovel-naturalness-review.md`
- Modify: `skill/longform-webnovel/references/review-system.md`
- Modify: `skill/longform-webnovel/references/operations.md`
- Modify: `tests/check_skill.py`
- Modify: `README.md`

- [ ] **Step 1: Capture a failing behavior scenario before editing instructions**

In a temporary novel project, present the current skill with this request and sample constraints: write a scene containing an account discrepancy, family interruption, and an unresolved recognition of handwriting. Record whether the produced workflow mechanically uses every suggested technique, optimizes sentence-length variance, inserts plotless objects, or fails to run the repetition audit. The expected RED observation is that the current skill cannot invoke a script that does not yet appear in its routing or commit transaction.

- [ ] **Step 2: Add a static package test and verify RED**

Add these assertions to `tests/check_skill.py`:

```python
assert (SKILL / "scripts" / "repetition_audit.py").is_file()
assert "repetition_audit.py" in text
review_text = (SKILL / "references" / "webnovel-naturalness-review.md").read_text(encoding="utf-8")
assert "rhetorical-symmetry" in review_text
assert "externalNaturalness" in review_text
```

Run: `python tests/check_skill.py`

Expected: FAIL because routing and reference terms have not been added.

- [ ] **Step 3: Update the references with decision-changing guidance**

Make the following contracts explicit and consistent across the four references:

- Add naturalness categories `echo-repetition`, `modifier-overuse`, `rhetorical-symmetry`, and `cadence-packaging` to the review table and validator set.
- Require `repetition_audit.py` after every new or modified chapter, comparing all earlier committed chapters for a short story and the recent five chapters by default for a serial.
- Require every surviving exact or near finding to have a hash-bound `repetitionExceptions` entry with a concrete editorial reason.
- Explain that exact numbers may coexist with a viewpoint character's rough estimate only when both affect the scene; never invent figures to simulate human authorship.
- Allow short reactions, interrupted dialogue, misunderstandings, uncertainty, action anchors, and low-plot-load texture only when they express viewpoint, relationship, world continuity, or consequence.
- Explicitly reject blanket adverb deletion, plotless detail insertion, forced hesitation, and optimizing sentence-count or variance metrics.
- Explain how to transcribe Zhuque highlights into `externalNaturalness`, and that unmatched highlights or overall percentages alone do not trigger revision.
- Preserve the one-targeted-revision limit and full post-edit rerun.

- [ ] **Step 4: Update `SKILL.md`, README, and validation category constants**

Add `repetition_audit.py` to the chapter transaction before prose lint, add its report to staging, and list it in the scripts section. Update `VALID_NATURALNESS_CATEGORY` in `validate_project.py` with the four new categories. Add one README capability bullet and the focused repetition test command.

- [ ] **Step 5: Re-run the behavior scenario with the revised skill**

Use the same temporary-project request. Success requires the worker to select only scene-supported techniques, reject variance optimization and purposeless detail, run both deterministic audits, and report evidence instead of an AI probability. If the chosen execution mode does not authorize an independent worker, document that behavioral forward-testing was not run and rely only on deterministic fixtures; do not claim agent-behavior validation.

- [ ] **Step 6: Run package and naturalness tests, then commit**

Run:

```powershell
python tests/check_skill.py
python skill/longform-webnovel/tests/test_naturalness_gate.py
python skill/longform-webnovel/tests/test_repetition_audit.py
```

Expected: structure validation prints `Skill structure is valid`; both unittest files end in `OK`.

```powershell
git add skill/longform-webnovel/SKILL.md skill/longform-webnovel/references/prose-naturalization.md skill/longform-webnovel/references/webnovel-naturalness-review.md skill/longform-webnovel/references/review-system.md skill/longform-webnovel/references/operations.md skill/longform-webnovel/scripts/validate_project.py tests/check_skill.py README.md
git commit -m "docs: enforce naturalness gate v2 workflow"
```

### Task 6: Full Verification and Installed Skill Sync

**Files:**
- Source: `skill/longform-webnovel/`
- Destination: `C:/Users/admin/.codex/skills/longform-webnovel/`

- [ ] **Step 1: Compile every Python script**

Run: `python -m py_compile skill/longform-webnovel/scripts/*.py`

On PowerShell, expand paths explicitly if the wildcard is not accepted:

```powershell
Get-ChildItem skill\longform-webnovel\scripts\*.py | ForEach-Object { python -m py_compile $_.FullName }
```

Expected: exit code 0 with no syntax errors.

- [ ] **Step 2: Run the full repository verification**

```powershell
python tests/check_skill.py
python tests/test_longform_webnovel.py
python skill/longform-webnovel/tests/test_naturalness_gate.py
python skill/longform-webnovel/tests/test_repetition_audit.py
python C:\Users\admin\.codex\skills\.system\skill-creator\scripts\quick_validate.py skill\longform-webnovel
git diff --check
git status --short
```

Expected: every Python command exits 0, quick validation reports a valid skill, `git diff --check` prints nothing, and status contains only intended tracked changes or is clean after task commits.

- [ ] **Step 3: Smoke-test the original failure and a legitimate exception**

Create a temporary chapter containing the previously missed long sentence twice and run `repetition_audit.py`; assert JSON contains `exact-sentence-duplicate`. Then validate a temporary project first without a disposition and observe a blocking error, add a matching hash-bound exception, and observe that the repetition error disappears.

- [ ] **Step 4: Request write permission and synchronize the installed skill**

After source verification succeeds, request permission for `C:\Users\admin\.codex\skills\longform-webnovel`. Copy only the contents of `skill\longform-webnovel` into that exact destination. Do not copy repository docs or tests into the installation unless they already belong inside the skill directory.

```powershell
Copy-Item -Path skill\longform-webnovel\* -Destination C:\Users\admin\.codex\skills\longform-webnovel -Recurse -Force
```

- [ ] **Step 5: Verify installed files independently**

```powershell
python C:\Users\admin\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\admin\.codex\skills\longform-webnovel
python C:\Users\admin\.codex\skills\longform-webnovel\tests\test_naturalness_gate.py
python C:\Users\admin\.codex\skills\longform-webnovel\tests\test_repetition_audit.py
```

Expected: all commands exit 0. Report the source commit IDs, installed path, exact test counts, and any behavioral-forward-test limitation. Do not push the branch unless the user separately authorizes it.
