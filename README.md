# PDF Generation

把 Markdown 排成一份像样的 PDF。解析用 pandoc，排版用自带 Typst 模板，渲染用 Typst——不装 TeX Live，也不需要 Eisvogel。

- **七种版式**：报告、文章、信函、笔记、书、教材、小说
- **可调排版**：四十多个旋钮，从纸张到章节标题配色都能逐项改
- **会先问再动手**：内置 Clarify 阶段，只问会改变成品的问题，并给出推荐值
- **自包含产物**：生成的 `.typ` 内联了整个模板，可直接 `typst compile` 复现

## 依赖

| 工具 | 版本 | 安装 |
|------|------|------|
| Typst | ≥ 0.15 | `winget install Typst.Typst` / `scoop install typst` / `brew install typst` |
| pandoc | ≥ 3.1 | `winget install JohnMacFarlane.Pandoc` / `brew install pandoc` |
| Python | ≥ 3.9 | 系统自带即可，无第三方包 |

中文字体建议装 **Noto Serif SC** 与 **Noto Sans SC**（或思源宋体/黑体）。Typst 自带西文与等宽字体，不需要额外安装。

装好后自检：

```bash
python scripts/build_pdf.py doctor
```

## 安装到 Agent

**DSH（首选）**：把整个目录放到 `~/.dsh/skills/pdf-generation/`，重启会话或重新加载技能列表即可。

**Claude Code**：放到 `~/.claude/skills/pdf-generation/`。

**其他 Agent**：`SKILL.md` 不依赖任何宿主专有工具——需要提问时它会说「有结构化提问工具就用，没有就用编号文本」。把目录放进对方的 skills 目录，或在系统提示里引用 `SKILL.md` 均可。

## 30 秒上手

```bash
# 1. 看一眼内容，拿到建议 Kind
python scripts/build_pdf.py detect report.md

# 2. 生成（默认 report，A4，自动出封面和目录）
python scripts/build_pdf.py build report.md

# 3. 换一种版式
python scripts/build_pdf.py build letter.md --kind letter

# 4. 调排版
python scripts/build_pdf.py build report.md --set page.margin=2cm --set color.palette=indigo
```

产物在源文件旁边：`report.pdf`（交付）、`report.typ`（自包含中间件）、`.pdfgen/report/p3.png`（自检抽页）。

## 七种 Kind

| Kind | 默认纸张 | 封面 | 目录 | 特点 |
|------|----------|------|------|------|
| `report` | A4 | 标题 + 报告人/机构/日期 | 2 级 | 默认，通用报告 |
| `article` | A4 | 无，首页标题块 + 摘要 | 无 | 单篇文章 |
| `letter` | A4 | 无 | 无 | 发件人/收件人/称呼/落款 |
| `note` | A4 | 无 | 无 | 紧凑，可开语义块 |
| `book` | 6×9 | 有 | 2 级 | 章起新页、页眉、首行缩进 |
| `textbook` | A4 | 有 | 3 级 | 定理/定义/例题/习题 |
| `novel` | A5 | 有 | 仅章 | 第 N 章、首字下沉、段首缩进 |

Kind 可以直接写在 frontmatter：`kind: novel`，也可以 `--kind novel`。

## 调排版

所有排版参数在一个 Style spec 里，优先级：`--set` > frontmatter（元数据）> `<stem>.doc.yml` > Kind 默认 > 全局默认。

```yaml
# report.doc.yml
kind: report
style:
  page:
    margin: 2.4cm
  text:
    size: 10.5pt
    first-line-indent: 0em
  heading:
    size-1: 18pt
    rule: true
  color:
    palette: indigo
```

```bash
python scripts/build_pdf.py style report.md --write report.doc.yml  # 导出完整 spec
python scripts/build_pdf.py build report.md                          # 自动读取 report.doc.yml
```

未知 key 会直接报错并给出相近建议，不会静默失效。全部旋钮见 [references/style-knobs.md](references/style-knobs.md)。

## 目录结构

```
pdf-generation/
├── SKILL.md                 # 给 agent 的操作说明（流程、Clarify、命令）
├── README.md                # 本文
├── CONTEXT.md               # 术语表
├── docs/adr/                # 两个关键决策的记录
├── template/                # Typst 模板（构建时内联进产物）
│   ├── 00-util.typ          # 小工具：中文数字、页边距、纸张
│   ├── 20-frontmatter.typ   # 封面、文章标题块、目录、信函头尾
│   ├── 30-blocks.typ        # 定理/定义/例题等语义块
│   ├── 40-kinds.typ         # 小说章首、首字下沉
│   ├── 90-doc.typ           # 主装配：set 规则 + 前置件 + 正文
│   └── meta.typ             # pandoc 元数据模板
├── filters/semantic.lua     # ::: div → 语义块；章首首段标记
├── scripts/
│   ├── build_pdf.py         # detect / build / style / check / doctor
│   └── gen_style_docs.py    # 从脚本里的旋钮表重新生成 style-knobs.md
├── references/              # kinds / style-knobs / authoring / troubleshooting
└── examples/                # 七种 Kind 各一份样张
```

## 已知限制

- **不做参考文献**：v1 没有 bibliography/citation 支持。
- **没有边注、代码行号**。
- Typst 0.15 在段距接近 0 时会把下一段抬高半行；构建脚本会把小段距抬到 4.5pt，所以书/小说会有一点点段间距（这是刻意的）。
- 不联网拉 Typst 包，模板全部内置；想换观感请改旋钮，而不是换包。

## 示例

`examples/` 下每种 Kind 一份可直接构建的样张：

```bash
python scripts/build_pdf.py build examples/report.md
python scripts/build_pdf.py build examples/letter.md
python scripts/build_pdf.py build examples/book/book.md examples/book/ch01.md examples/book/ch02.md
```

## License

MIT
