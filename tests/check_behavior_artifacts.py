#!/usr/bin/env python3
"""Check observable invariants of the isolated skill behavior cases, not prose quality."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL = ROOT / 'skill' / 'longform-webnovel'


def check_artifacts(run: Path, skill: Path) -> dict:
    errors: list[str] = []
    checked: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    def read(path: Path) -> str:
        return path.read_text(encoding='utf-8')

    for number in range(1, 8):
        case = run / f'case-{number}'
        require((case / 'result.md').is_file(), f'case {number}: missing result.md')
        record = case / 'execution.json'
        require(record.is_file(), f'case {number}: missing execution.json')
        if record.is_file():
            require(isinstance(json.loads(read(record)), dict), f'case {number}: execution record must be an object')

    for number in (1, 2, 3, 6, 7):
        case = run / f'case-{number}'
        require(not list(case.rglob('project.json')), f'case {number}: unexpectedly initialized a formal project')
        require(not list(case.rglob('*-review.json')), f'case {number}: unexpectedly generated formal review JSON')
        for directory in ('canon', 'state', 'chapters'):
            require(not (case / directory).exists(), f'case {number}: unexpectedly created {directory}/')
    checked.append('light-workflow-file-boundaries')

    for number in (1, 3):
        result = run / f'case-{number}' / 'result.md'
        if result.is_file():
            prose = read(result)
            require(not any(char in prose for char in '\u300c\u300d\u300e\u300f'), f'case {number}: corner quotes in delivered prose')
            require(prose.count('\u201c') == prose.count('\u201d') > 0, f'case {number}: missing or unbalanced Chinese double quotes')
    checked.append('dialogue-quotation-format')

    original = '“我很难过。”姐姐说。她说得很平，像怕把这句话碰碎。我本来准备好的笑话，一个字也没说。窗外的雨还在下。'
    emotion = run / 'case-2/result.md'
    if emotion.is_file():
        require(original in read(emotion), 'case 2: requested original passage was not preserved')
    checked.append('approved-original-preserved')

    for number in (4, 5):
        project = run / f'case-{number}/project'
        index_path = project / 'project.json'
        if not index_path.is_file():
            errors.append(f'case {number}: missing formal project')
            continue
        index = json.loads(read(index_path))
        require(index.get('lastCommittedChapter') == 1, f'case {number}: expected exactly one committed chapter')
        require(index.get('publishingPackage', {}).get('status') == 'unconfirmed', f'case {number}: pending packaging was falsely activated')
        state = json.loads(read(project / 'state/story-state.json'))
        core_values = [state.get('storyTime'), state.get('location')]
        core_values.extend(state.get('protagonist', {}).get(field) for field in ('goal', 'condition'))
        require(all(isinstance(value, str) and value.strip() and value not in {'待填写', '待确认', '待规划'} for value in core_values),
                f'case {number}: story state still contains unfilled fixture values')
        chapter_files = list((project / 'chapters').glob('*.md'))
        if number == 5 and len(chapter_files) == 1:
            require(chapter_files[0].read_bytes() == (run / 'case-5/candidate.md').read_bytes(), 'case 5: final chapter differs from approved candidate')
        result = subprocess.run([sys.executable, str(skill / 'scripts/validate_project.py'), str(project)], capture_output=True, text=True)
        require(result.returncode == 0, f'case {number}: project validation failed: {result.stdout or result.stderr}')
    checked.append('formal-commit-and-final-version-validation')

    slicing = run / 'case-7'
    source, head, tail = [slicing / name for name in ('draft.md', 'head.md', 'tail.md')]
    if all(path.is_file() for path in (source, head, tail)):
        require(head.read_bytes() + tail.read_bytes() == source.read_bytes(), 'case 7: head and tail do not reassemble the exact source')
        expected_hash = read(slicing / 'input-sha256.txt').strip()
        require(hashlib.sha256(source.read_bytes()).hexdigest() == expected_hash, 'case 7: original draft was modified')
        metrics = subprocess.run([sys.executable, str(skill / 'scripts/chapter_metrics.py'), str(head)], capture_output=True, text=True)
        require(metrics.returncode == 0, f'case 7: cannot measure exported chapter: {metrics.stderr}')
        if metrics.returncode == 0:
            count = json.loads(metrics.stdout)['contentChars']
            require(abs(count - 2500) <= 100, f'case 7: first slice has {count} effective characters')
    else:
        errors.append('case 7: missing draft.md, head.md or tail.md')
    checked.append('default-cut-size-and-lossless-tail')
    return {'ok': not errors, 'checks': checked, 'errors': errors,
            'scope': 'Artifact checks do not establish prose quality, blind review, or all model actions.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path, help='Saved case-1 through case-7 artifact directory')
    parser.add_argument('--skill-dir', type=Path, default=DEFAULT_SKILL)
    args = parser.parse_args()
    try:
        result = check_artifacts(args.run.resolve(), args.skill_dir.resolve())
    except (OSError, ValueError, KeyError) as exc:
        result = {'ok': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
