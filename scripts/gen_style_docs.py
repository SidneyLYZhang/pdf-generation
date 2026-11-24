"""Generate the reference tables that must not drift from the code.

Two generated regions:

- `references/style-knobs.md` — the whole file comes from `KNOBS` and `PRESETS`.
- `references/typography.md` — only the rule table, spliced between two markers;
  the prose around it is hand-written.

`--check` compares instead of writing, which is what the tests and CI run.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_pdf as b  # noqa: E402

STYLE_KNOBS = ROOT / "references" / "style-knobs.md"
TYPOGRAPHY = ROOT / "references" / "typography.md"
RULES_BEGIN = "<!-- BEGIN generated: rules -->"
RULES_END = "<!-- END generated: rules -->"
METRICS_BEGIN = "<!-- BEGIN generated: metrics -->"
METRICS_END = "<!-- END generated: metrics -->"

DESC = {
    "page.paper": "纸张：a4 / a5 / 6x9 / letter",
    "page.margin": "四边页边距（下面两个轴写 auto 时用它）",
    "page.margin-x": "左右页边距（版心宽度）；auto = 跟随 page.margin（style --write 写出的是解析后的值）",
    "page.margin-y": "上下页边距；auto = 跟随 page.margin（style --write 写出的是解析后的值）",
    "page.gutter": "装订线（内侧额外留白）",
    "text.font": "正文字体栈，按顺序取字形",
    "text.heading-font": "标题字体栈",
    "text.size": "正文字号",
    "text.leading": "行距（行与行之间的额外距离）",
    "text.paragraph-spacing": "段间距；小于 4.5pt 会被抬到 4.5pt（Typst 0.15 限制）",
    "text.first-line-indent": "段首缩进，中文书籍习惯 2em",
    "text.justify": "两端对齐",
    "text.hyphenate": "西文断词",
    "text.lang": "语言标签，zh / en / auto",
    "heading.size-1": "一级标题字号",
    "heading.size-2": "二级标题字号",
    "heading.size-3": "三级标题字号",
    "heading.color": "标题颜色",
    "heading.numbering": "标题编号格式：1.1 / 1.a / none",
    "heading.page-break-before": "一级标题是否另起一页",
    "heading.space-before": "标题上方留白",
    "heading.space-after": "标题下方留白",
    "heading.rule": "一级标题下是否加细线",
    "color.palette": "配色：teal / indigo / sepia / mono",
    "color.accent": "强调色（色带、语义块边线、链接默认值）",
    "color.ink": "正文颜色",
    "color.muted": "次要文字颜色（页眉、题注、日期）",
    "color.rule": "细线颜色",
    "color.link": "链接颜色",
    "color.code-bg": "代码块底色",
    "color.tint": "语义块与摘要底色",
    "furniture.header": "页眉：none / title / book（奇偶交替）/ chapter",
    "furniture.header-rule": "页眉下细线",
    "furniture.page-number": "页码位置：none / footer-center / footer-right / footer-outside",
    "furniture.page-number-format": "页码格式，Typst numbering 写法，如 1 / a / i",
    "cover.enabled": "是否生成封面",
    "cover.style": "封面样式：band（色带）/ full（整版色）/ minimal（极简）",
    "cover.tagline": "封面上的短句",
    "cover.logo": "封面 logo 图片路径",
    "toc.enabled": "是否生成目录",
    "toc.depth": "目录深度（标题层级）",
    "toc.title": "目录标题文字",
    "float.figure-caption": "图片题注位置：top / bottom",
    "float.table-caption": "表格题注位置：top / bottom",
    "float.numbering": "图表编号格式，如 1 / (1) / none",
    "float.figure-width": "图片默认宽度（占正文宽度）",
    "code.theme": "代码高亮：default / none",
    "code.size": "代码字号",
    "code.header": "代码块顶部语言栏",
    "code.line-numbers": "代码行号；单块用 `{.line-numbers}` / `{.no-line-numbers}` 覆盖",
    "math.numbering": "公式编号格式，如 1 / (1) / none",
    "note.style": "注释位置：footnote（页脚）/ margin（页边）",
    "note.width": "边注栏宽度",
    "note.gap": "边注与正文之间的间距",
    "note.size": "边注字号",
    "cite.enabled": "是否生成参考文献表；true / false / auto（auto = 声明了 `bibliography` 才生成）",
    "cite.style": "CSL 样式：内置名（`ieee` / `apa` / `gb-7714-2015-numeric` …）或 `.csl` 路径；auto 按语言与 Kind 取默认",
    "cite.title": "参考文献标题；auto 按语言取「参考文献 / References」",
    "semantic.numbering": "语义块编号格式，如 1 / (1)；none 表示只显示标签不编号",
    "novel.dropcap": "章首首字下沉",
    "novel.chapter-prefix": "自动生成「第 N 章」前缀",
}

# `lengthauto` is a length that may also say auto; show the friendlier name.
TYPE_LABELS = {"lengthauto": "length｜auto"}


def render_style_knobs() -> str:
    out = []
    out.append("# Style spec 旋钮\n")
    out.append("一个文档的排版由一份 Style spec 决定。它是 `doc.yml` 里 `style:` 的内容，构建时与 Kind 默认合并成完整取值。\n")
    out.append("## 优先级\n")
    out.append("从高到低：\n")
    out.append("1. `--set key=value`（一次性覆盖）")
    out.append("2. Markdown frontmatter（只影响元数据：标题、作者、日期、机构、letter 字段）")
    out.append("3. `<首个输入文件>.doc.yml` 的 `style:`")
    out.append("4. Kind 默认值")
    out.append("5. 全局默认值\n")
    out.append("未知 key 会直接报错，并给出最接近的合法项。\n")
    out.append(
        f"另有一处默认随语言推导：纯英文 A4 文档的左右页边距取 `{b.ENGLISH_MARGIN_X}`，"
        f"让每行落进 {b.WESTERN_MEASURE[0]}–{b.WESTERN_MEASURE[1]} 字符的区间；上下边距不变。"
        "作者显式设置的页边距、自带页边距的 Kind、以及 `note` 不受影响。\n"
    )

    out.append("## 全局默认\n")
    out.append("| 旋钮 | 类型 | 默认值 | 说明 |")
    out.append("|------|------|--------|------|")
    for key, (typ, default) in b.KNOBS.items():
        shown = str(default).lower() if isinstance(default, bool) else default
        out.append(f"| `{key}` | {TYPE_LABELS.get(typ, typ)} | `{shown}` | {DESC.get(key, '')} |")

    out.append("\n## 各 Kind 的覆盖\n")
    out.append("只列出与该 Kind 的全局默认不同的项；其余沿用上表。\n")
    keys = sorted({k for preset in b.PRESETS.values() for k in preset})
    header = "| 旋钮 | " + " | ".join(b.KINDS) + " |"
    out.append(header)
    out.append("|" + "------|" * (len(b.KINDS) + 1))
    for key in keys:
        cells = []
        for kind in b.KINDS:
            value = b.PRESETS[kind].get(key)
            cells.append(f"`{value}`" if value is not None else "—")
        out.append(f"| `{key}` | " + " | ".join(cells) + " |")

    out.append("\n## 取值格式\n")
    out.append("- 长度：`12pt`、`2.4cm`、`2em`、`0pt`")
    out.append("- 比例：`82%`")
    out.append("- 颜色：6 位十六进制，`#22645E` 或 `22645E`")
    out.append("- 布尔：`true` / `false`")
    out.append("- 字体栈：`[\"Libertinus Serif\", \"Noto Serif SC\"]` 或逗号分隔字符串\n")

    out.append("## 示例\n")
    out.append("```yaml")
    out.append("kind: report")
    out.append("style:")
    out.append("  page:")
    out.append("    margin: 2.4cm")
    out.append("  heading:")
    out.append("    size-1: 18pt")
    out.append("    rule: true")
    out.append("  color:")
    out.append("    palette: indigo")
    out.append("```\n")
    out.append("```bash")
    out.append("python scripts/build_pdf.py build doc.md --set heading.size-1=18pt")
    out.append("python scripts/build_pdf.py build doc.md --doc doc.doc.yml")
    out.append("python scripts/build_pdf.py style doc.md --write doc.doc.yml")
    out.append("```")
    return "\n".join(out) + "\n"


def render_rule_table() -> str:
    lines = [
        "| 规则 | 档 | 判定 | 建议区间 |",
        "|------|----|------|----------|",
    ]
    for rule, severity, _ in b.PRINCIPLE_RULES:
        what, band = b.RULE_SUMMARY[rule]
        label = "阻断" if severity == "error" else "警告"
        lines.append(f"| `{rule}` | {label} | {what} | {band} |")
    return "\n".join(lines)


def render_metrics_table() -> str:
    lines = ["| 字族 | 行盒 |", "|------|------|"]
    for font in sorted(b.LINE_BOX_EM):
        lines.append(f"| `{font}` | {b.LINE_BOX_EM[font]:.3f}em |")
    return "\n".join(lines)


def splice(existing: str, begin: str, end: str, body: str) -> str:
    start = existing.find(begin)
    stop = existing.find(end)
    if start < 0 or stop < start:
        raise b.SpecError(
            f"{TYPOGRAPHY.name} 缺少 {begin} 或 {end}：把这两行标记各占一行补进去"
            "（不要缩进），再重新生成"
        )
    return existing[: start + len(begin)] + "\n" + body + "\n" + existing[stop:]


def render_typography(existing: str) -> str:
    """Fill both generated regions; everything around them stays hand-written."""
    text = splice(existing, RULES_BEGIN, RULES_END, render_rule_table())
    return splice(text, METRICS_BEGIN, METRICS_END, render_metrics_table())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 references 里由代码决定的表格")
    parser.add_argument("--check", action="store_true", help="只比对不写入；不一致时退出码 1")
    args = parser.parse_args(argv)

    if not TYPOGRAPHY.exists():
        print(
            f"缺少 {TYPOGRAPHY.relative_to(ROOT)}：先写这份规范文档，再回来生成表格",
            file=sys.stderr,
        )
        return 1
    try:
        rendered = [
            (STYLE_KNOBS, render_style_knobs()),
            (TYPOGRAPHY, render_typography(TYPOGRAPHY.read_text(encoding="utf-8"))),
        ]
    except b.SpecError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    stale = []
    for path, text in rendered:
        current = path.read_text(encoding="utf-8")
        if current == text:
            print(f"ok    {path.relative_to(ROOT)}")
            continue
        stale.append(path)
        if not args.check:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    if args.check and stale:
        for path in stale:
            print(f"stale {path.relative_to(ROOT)}", file=sys.stderr)
        print("文档与实现不一致，跑 `python scripts/gen_style_docs.py` 重新生成", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
