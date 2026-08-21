#!/usr/bin/env python3
"""List, preview, or apply a language style profile to a webnovel project."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from webnovel_io import CURRENT_PROJECT_SCHEMA, backup_files, load_json, restore_backup, utc_now, write_json_atomic, write_text_atomic
from webnovel_style import PRESETS, render_custom_profile, render_profile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List available presets")
    parser.add_argument("--show", choices=sorted(PRESETS), help="Print one rendered preset")
    parser.add_argument("--project", type=Path, help="Project to update")
    parser.add_argument("--primary", choices=sorted(PRESETS), help="Primary style preset")
    parser.add_argument("--secondary", choices=sorted(PRESETS), help="Optional secondary style preset")
    parser.add_argument("--custom-id", help="Stable lowercase id for a custom technique profile")
    parser.add_argument("--custom-title", help="Display title for a custom technique profile")
    parser.add_argument("--custom-file", type=Path, help="UTF-8 technique card for a custom profile")
    parser.add_argument("--notes", default="", help="Project-specific style constraints")
    parser.add_argument("--confirmed", action="store_true", help="Confirm a style change after chapters have been committed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    selected_actions = sum((args.list, args.show is not None, args.project is not None))
    if selected_actions != 1:
        parser.error("choose exactly one of --list, --show, or --project")
    if args.list:
        print(json.dumps({key: value["name"] for key, value in PRESETS.items()}, ensure_ascii=False, indent=2))
        return 0
    if args.show:
        print(render_profile(args.show))
        return 0
    custom_args = (args.custom_id, args.custom_title, args.custom_file)
    if args.primary and any(custom_args):
        parser.error("use either --primary or the complete custom profile arguments")
    if not args.primary and not all(custom_args):
        parser.error("--project requires --primary or --custom-id + --custom-title + --custom-file")
    if args.secondary and args.secondary == args.primary:
        parser.error("--secondary must differ from --primary")
    if args.custom_id and args.secondary:
        parser.error("custom profiles cannot use --secondary; express the blend in the technique card")

    root = args.project.expanduser().resolve()
    project_path = root / "project.json"
    profile_path = root / "canon" / "style-profile.md"
    project = load_json(project_path)
    if project.get("schemaVersion") != CURRENT_PROJECT_SCHEMA:
        raise SystemExit("Project schema is old; run migrate_project.py first")
    committed = project.get("lastCommittedChapter", 0)
    if not isinstance(committed, int) or isinstance(committed, bool) or committed < 0:
        raise SystemExit("Invalid lastCommittedChapter")
    if committed > 0 and not args.confirmed:
        raise SystemExit("Changing language style after committed chapters is a major decision; pass --confirmed after author approval")

    if args.custom_id:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", args.custom_id):
            parser.error("--custom-id must use lowercase letters, digits, and hyphens")
        technique_card = args.custom_file.expanduser().read_text(encoding="utf-8")
        if not 100 <= len(technique_card.strip()) <= 6000:
            parser.error("--custom-file must contain 100-6000 characters")
        selected_primary = f"custom:{args.custom_id}"
        selected_secondary = None
        content = render_custom_profile(args.custom_id, args.custom_title, technique_card, args.notes)
    else:
        selected_primary = args.primary
        selected_secondary = args.secondary
        content = render_profile(args.primary, args.secondary, args.notes)
    changed_at = utc_now()
    proposed = dict(project)
    proposed["styleProfile"] = {
        "primary": selected_primary,
        "secondary": selected_secondary,
        "status": "active",
        "updatedAt": changed_at,
    }
    proposed["updatedAt"] = changed_at
    result = {
        "ok": True,
        "dryRun": args.dry_run,
        "primary": selected_primary,
        "secondary": selected_secondary,
        "project": str(root),
    }
    if not args.dry_run:
        backup = backup_files(root, [Path("project.json"), Path("canon/style-profile.md")], "style-profile")
        try:
            write_text_atomic(profile_path, content)
            write_json_atomic(project_path, proposed)
        except Exception:
            restore_backup(root, backup)
            raise
        result["backup"] = str(backup)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
