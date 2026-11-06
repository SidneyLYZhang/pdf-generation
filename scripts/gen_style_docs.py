import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_pdf as b

DESC = {
    "page.paper": "纸张：a4 / a5 / 6x9 / letter",
    "page.margin": "四边页边距",
    "page.gutter": "装订线（内侧额外留白）",
    "page.columns": "分栏数，1 或 2",
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
    "float.numbering": "图表编号格式，如 1.1 / none",
    "float.figure-width": "图片默认宽度（占正文宽度）",
    "code.theme": "代码高亮：default / none",
    "code.size": "代码字号",
    "code.header": "代码块顶部语言栏",
    "math.numbering": "公式编号格式，如 1.1 / none",
    "semantic.numbering": "语义块编号格式；none 表示只显示「定理/例题」标签不编号",
    "novel.dropcap": "章首首字下沉",
    "novel.chapter-prefix": "自动生成「第 N 章」前缀",
    "letter.sender": "信函发件人（也可写在 frontmatter letter.from）",
    "letter.recipient": "信函收件人（frontmatter letter.to）",
    "letter.date": "信函日期（frontmatter letter.date）",
    "letter.subject": "信函主题（frontmatter letter.subject）",
    "letter.salutation": "称呼（frontmatter letter.salutation）",
    "letter.closing": "落款敬语（frontmatter letter.closing）",
    "letter.signature": "署名（frontmatter letter.signature）",
}

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

out.append("## 全局默认\n")
out.append("| 旋钮 | 类型 | 默认值 | 说明 |")
out.append("|------|------|--------|------|")
for key, (typ, default) in b.KNOBS.items():
    out.append(f"| `{key}` | {typ} | `{default}` | {DESC.get(key, '')} |")

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

target = Path(__file__).resolve().parent.parent / "references" / "style-knobs.md"
target.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"wrote {target} ({len(out)} lines)")
