#!/usr/bin/env python3
"""Check a title or apply a confirmed title and cover-prompt package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from webnovel_io import CURRENT_PROJECT_SCHEMA, backup_files, load_json, restore_backup, utc_now, write_json_atomic, write_text_atomic


GENERIC_EXACT = {
    "重生归来",
    "逆天改命",
    "都市修仙",
    "绝世武神",
    "无敌战神",
    "最强赘婿",
    "末世求生",
    "巅峰人生",
}
FORMULAIC_PATTERNS = (
    (re.compile(r"^(开局|重生|穿越|觉醒).{0,4}(系统|签到|无敌|逆袭)"), "常见开局/系统公式"),
    (re.compile(r"^(最强|绝世|无敌|极品).{0,6}(神|王|帝|婿|高手|战神)$"), "常见最强身份公式"),
    (re.compile(r"^我在.{1,8}(当|做|成了|修仙|种田)$"), "常见‘我在某处’公式"),
)
COVER_STYLES = (
    "editorial-impact",
    "classical-calligraphy",
    "cinematic-3d",
    "action-display",
    "emotional-handwritten",
    "mystery-file",
)


def analyze_title(title: str) -> dict:
    normalized = re.sub(r"[\s《》〈〉【】]", "", title)
    errors = []
    warnings = []
    if len(normalized) < 4:
        errors.append("书名少于 4 个字符，辨识度通常不足")
    if len(normalized) > 30:
        warnings.append("书名超过 30 个字符，封面排版和口头传播成本较高")
    if normalized in GENERIC_EXACT:
        errors.append("书名属于高频泛化标题")
    for pattern, message in FORMULAIC_PATTERNS:
        if pattern.search(normalized):
            warnings.append(message)
    return {
        "title": title.strip(),
        "normalized": normalized,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "requiresPublicExactSearch": True,
    }


def read_bounded(path: Path, label: str, minimum: int, maximum: int) -> str:
    content = path.expanduser().read_text(encoding="utf-8").strip()
    if not minimum <= len(content) <= maximum:
        raise ValueError(f"{label} must contain {minimum}-{maximum} characters")
    return content


def default_title_layout(title: str, style: str = "editorial-impact") -> str:
    shared = f"""- 准确文字：仅使用书名“{title}”，不增字、不漏字、不改字，不用拼音或英文替代；阅读顺序必须清楚。
- 缩略图标准：按 120×160 像素预览时，主标题仍须在 1 秒内辨认；四边保留至少画面宽度 5% 的安全距离，不得遮挡人物眼睛、嘴巴和核心道具。
- 作者名：使用“作者：〔后台真实笔名〕”占位，字号为主标题的 20%–26%，不得由模型编造笔名。"""
    profiles = {
        "editorial-impact": """- 版式：主标题位于上半部，最多两行横排，标题块占画面宽度 72%–82%、高度 24%–34%，主副层级明确。
- 字形：宽扁、字面饱满的重黑标题骨架，横竖笔画接近等粗，方头略带外扩切角，不使用普通文档黑体的平直效果。
- 字效：暖白或亮橙正面，先加窄白色内描边，再加深红或深蓝外包边；向右下投射短硬阴影，局部高光只落在上缘，形成海报式浅浮雕。
- 图文关系：标题可压住人物肩部或衣角不超过 6%，人物头部与关键动作完整露出；标题背后降低纹理与高光密度。""",
        "classical-calligraphy": """- 版式：主标题在左中部或画面中轴纵排 2–3 列，列间错落，标题块占画面宽度 30%–42%、高度 55%–70%，从上到下、从右向左阅读。
- 字形：瘦长榜书行楷骨架，重心略高，起收笔有锋，粗细反差明显；笔画保留可见飞白、枯笔和墨色浓淡，不做电脑楷体。
- 字效：旧宣纸暖白与哑光金箔混合材质，细暗红外描边，极浅纸面投影；配一枚小号朱文题签作层级点缀，不承载作者名。
- 图文关系：竖排标题像诏令或题签压在场景前层，可覆盖衣摆或器物边缘不超过 8%，不得遮挡人物脸部与故事关键物证。""",
        "cinematic-3d": """- 版式：主标题置于上半部中央，两行横排，第一行占宽约 76%，第二行占宽约 58%；小号副题独立置于标题下方窄横条。
- 字形：宽扁几何重黑骨架，字腔紧、笔画粗、端点方正带切角，主关键词放大 115%–130%。
- 字效：亮橙到金黄硬渐变正面，窄象牙白内高光、深红包边、黑蓝第二层描边；向右下挤出 6–10 像素金属侧面并配硬投影，边缘有少量磨砂颗粒，禁止塑料发光感。
- 图文关系：人物与门、阶梯或城市透视线共同指向标题，标题在人物前层但不压头部，背后用深色放射线强化轮廓。""",
        "action-display": """- 版式：主标题占画面下三分之一，整体向右上倾斜约 7 度，一至两行斜切排版，标题块占宽 82%–92%。
- 字形：超粗紧缩黑体骨架，方头刀锋切角，部分横画外伸形成速度感；关键词比其余文字大 20%，但保持同一阅读基线。
- 字效：暖白到橙红硬渐变正面，白色窄内高光、深褐粗外描边、黑色短投影，字腰穿过一条锐利红色速度线；不得使用模糊光晕。
- 图文关系：标题允许压住人物肩部、制服下缘或前景碎片 5%–10%，人物面部、徽章和手中物件必须完整可见。""",
        "emotional-handwritten": """- 版式：主标题沿人物视线留白侧排成 2–3 行错落结构，占宽 48%–64%、高度 28%–42%，行首不完全齐平但阅读顺序明确。
- 字形：粗手写骨架，字面大小有克制变化，笔触有停顿、回锋和干湿差，基线稳定，不做儿童涂鸦或纤细签名字。
- 字效：哑光暖白或低饱和绛红笔触，单层深色描边和向右下的柔和短阴影；只用一处与故事相关的折痕、裂线或波形融入笔画。
- 图文关系：文字与人物之间保留清楚呼吸区，可轻压衣角，不能跨过眼睛和嘴部；标题背后的光线保持均匀低纹理。""",
        "mystery-file": """- 版式：主标题置于上部窄区或右侧纵排，占画面宽度 28%–54%，周围保留大面积暗部；编号和日期只能作为小号辅助层。
- 字形：窄长宋黑混合骨架，横细竖重、字距紧，局部边缘像被档案裁刀截断，但每个汉字结构完整。
- 字效：骨白或警示红平面字，深黑细描边和轻微错版套印，不做霓虹、厚重金属或大面积发光。
- 图文关系：标题压在档案袋、门框或阴影前层，避开人物五官和线索物件；真实机构徽标、印章与编号格式不得出现。""",
    }
    return profiles[style] + "\n" + shared


def render_package(
    title: str,
    positioning: str,
    cover_prompt: str,
    negative_prompt: str,
    title_layout: str,
    research: str,
    checked_at: str,
) -> str:
    return f"""# 书名与封面包装

## 状态

- 包装状态：`active`
- 定名状态：`confirmed`
- 唯一性检查：`completed`
- 封面提示词状态：`ready`
- 小说名：{title}
- 检查时间：{checked_at}

## 定位

{positioning}

## 公开检索记录

{research}

精确检索只能降低撞名和俗套风险，不构成商标、版权或全网唯一性保证。

## 封面主提示词

{cover_prompt}

## 负面提示词

{negative_prompt or "低清晰度，错误文字，乱码标题，水印，平台标识，过度拥挤，主体被裁切，廉价素材拼贴，模仿具体艺术家风格"}

## 番茄成品规格

按番茄作者帮助中心公开要求，成品封面使用 600×800 像素、3:4 竖版，PNG 或 JPEG，文件不超过 5MB。成品必须包含准确书名“{title}”和作者笔名（替换为后台真实笔名），字迹清晰、完整、无遮挡；不得含外站 Logo、二维码、网址或水印。

## 书名排版与字体说明

{title_layout}

优先生成无文字封面底图，为书名、作者名和平台角标保留明确安全区；文字在后期排版，不依赖图像模型生成汉字。作者笔名不得由图像模型自行编造。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-title", help="Analyze one title without changing a project")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--positioning-file", type=Path)
    parser.add_argument("--cover-prompt-file", type=Path)
    parser.add_argument("--negative-prompt-file", type=Path)
    parser.add_argument("--title-layout-file", type=Path, help="Optional title typography and layout notes")
    parser.add_argument(
        "--cover-style",
        choices=COVER_STYLES,
        default="editorial-impact",
        help="Fallback title-effect profile used when --title-layout-file is omitted",
    )
    parser.add_argument("--research-notes-file", type=Path)
    parser.add_argument("--confirmed", action="store_true", help="Confirm changing a title after chapters have been committed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.check_title:
        print(json.dumps(analyze_title(args.check_title), ensure_ascii=False, indent=2))
        return 0
    required = (args.project, args.title, args.positioning_file, args.cover_prompt_file, args.research_notes_file)
    if not all(required):
        parser.error("use --check-title or provide --project, --title, --positioning-file, --cover-prompt-file, and --research-notes-file")

    title_result = analyze_title(args.title)
    if not title_result["ok"]:
        raise SystemExit("; ".join(title_result["errors"]))
    positioning = read_bounded(args.positioning_file, "positioning", 20, 800)
    cover_prompt = read_bounded(args.cover_prompt_file, "cover prompt", 80, 3000)
    research = read_bounded(args.research_notes_file, "research notes", 30, 3000)
    negative = read_bounded(args.negative_prompt_file, "negative prompt", 10, 1000) if args.negative_prompt_file else ""
    title_layout = (
        read_bounded(args.title_layout_file, "title layout", 30, 2000)
        if args.title_layout_file
        else default_title_layout(args.title.strip(), args.cover_style)
    )

    root = args.project.expanduser().resolve()
    project_path = root / "project.json"
    package_path = root / "canon" / "publishing-package.md"
    project = load_json(project_path)
    if project.get("schemaVersion") != CURRENT_PROJECT_SCHEMA:
        raise SystemExit("Project schema is old; run migrate_project.py first")
    committed = project.get("lastCommittedChapter", 0)
    if not isinstance(committed, int) or isinstance(committed, bool) or committed < 0:
        raise SystemExit("Invalid lastCommittedChapter")
    title_changed = project.get("title") != args.title.strip()
    if committed > 0 and title_changed and not args.confirmed:
        raise SystemExit("Changing the title after committed chapters is a major decision; pass --confirmed after author approval")

    checked_at = utc_now()
    content = render_package(args.title.strip(), positioning, cover_prompt, negative, title_layout, research, checked_at)
    proposed = dict(project)
    proposed["title"] = args.title.strip()
    proposed["publishingPackage"] = {
        "status": "active",
        "titleStatus": "confirmed",
        "uniquenessStatus": "completed",
        "coverPromptStatus": "ready",
        "updatedAt": checked_at,
    }
    proposed["updatedAt"] = checked_at
    result = {
        "ok": True,
        "dryRun": args.dry_run,
        "title": args.title.strip(),
        "titleWarnings": title_result["warnings"],
        "coverStyle": "custom" if args.title_layout_file else args.cover_style,
        "project": str(root),
    }
    if not args.dry_run:
        backup = backup_files(root, [Path("project.json"), Path("canon/publishing-package.md")], "publishing-package")
        try:
            write_text_atomic(package_path, content)
            write_json_atomic(project_path, proposed)
        except Exception:
            restore_backup(root, backup)
            raise
        result["backup"] = str(backup)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
