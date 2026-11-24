# PDF Generation

把 Markdown 排成一份像样的 PDF：**pandoc 解析，Typst 排版，不装 TeX Live**。

- **七种版式**：报告、文章、信函、笔记、书、教材、小说
- **可调排版**：五十多个旋钮，纸张、字体、行距、页眉、配色逐项可改
- **先问后做**：内置 Clarify 阶段，只问会改变成品的选择，并给推荐值
- **内容能力**：引文与 CSL 参考文献、图/表/公式/节交叉引用、边注、代码行号、mermaid/graphviz 图表、国际象棋棋谱（内联 staunton）
- **自包含产物**：生成的 `.typ` 内联整个模板，可直接 `typst compile` 复现；图片在输出目录之外、或文档用了棋谱时，按文件头那行现成命令加上 `--root` / `--package-path`

## 安装

见 [INSTALL.md](INSTALL.md)：依赖、字体、DSH / Claude Code / 其他 Agent 的放置方式、30 秒验证。

最小依赖：Typst ≥ 0.15、pandoc ≥ 3.1、Python ≥ 3.9。装好后：

```bash
python scripts/build_pdf.py doctor
```

## 30 秒上手

```bash
python scripts/build_pdf.py detect report.md          # 1. 看内容，拿建议 Kind
python scripts/build_pdf.py build report.md           # 2. 默认 report，A4，自动封面+目录
python scripts/build_pdf.py build letter.md --kind letter
python scripts/build_pdf.py build report.md --set page.margin=2cm --set color.palette=indigo
```

产物在源文件旁：`report.pdf`、`report.typ`、`.pdfgen/report/p3.png`（抽页）。

## 七种 Kind

| Kind | 默认纸张 | 特点 |
|------|----------|------|
| `report` | A4 | 默认；封面（报告人/机构/日期）、2 级目录、`1.1` 编号 |
| `article` | A4 | 无封面；首页标题块 + 摘要 + 关键词 |
| `letter` | A4 | 发件人/收件人/主题/称呼/落款，无目录无页码 |
| `note` | A4 | 紧凑；可开定理、提示等语义块 |
| `book` | 6×9 | 章起新页、奇偶页眉、首行缩进 |
| `textbook` | A4 | 3 级目录；定理/定义/例题/习题连续编号 |
| `novel` | A5 | 「第 N 章」、章首装饰、首字下沉 |

Kind 可以写在 frontmatter（`kind: novel`），也可以 `--kind novel`。细节见 [references/kinds.md](references/kinds.md)。

## 调排版

所有排版参数收敛在一个 Style spec 里，优先级：`--set` > `<stem>.doc.yml` > Kind 默认 > 全局默认；Markdown frontmatter 只提供元数据（标题、作者、`kind`、书目等）。

```yaml
# report.doc.yml
kind: report
style:
  page:
    margin: 2.4cm
  text:
    size: 10.5pt
  heading:
    size-1: 18pt
    rule: true
  color:
    palette: indigo
```

```bash
python scripts/build_pdf.py style report.md --write report.doc.yml  # 导出当前完整 spec
python scripts/build_pdf.py build report.md                        # 自动读取 report.doc.yml
```

未知旋钮会报错并给出最接近的三个合法名，不会静默失效。全部旋钮见 [references/style-knobs.md](references/style-knobs.md)。

## Markdown 写法

- 方言是钉死的 pandoc markdown：引文 `[@key]`、交叉引用 `@fig:`、围栏参数、图片题注、`::: {.theorem}` 语义块都能用。
- 引文要先在 frontmatter 里写 `bibliography: references.bib`，见 [references/citations.md](references/citations.md)。
- 数学 `$x$` 内侧不能有空格；LaTeX 命令用 `\alpha`、`\frac` 这类合法写法；`\label` / `\eqref` 可做公式交叉引用。
- 边注用 `[文字]{.sidenote}`、代码行号用 `{.line-numbers}`、图表用 ```` ```dot ```` 围栏、棋谱用 ```` ```fen ````。
- 信函字段写在 frontmatter 的 `letter:` 下，字符串内 `\n` 表示换行。
- 多文件：`build book.md ch01.md ch02.md`，第一个文件管元数据。

完整写法与坑见 [references/authoring.md](references/authoring.md)。

## 目录结构

```
pdf-generation/
├── SKILL.md                 # 给 agent 的操作说明（六步流程 + 完成判据）
├── INSTALL.md               # 安装：用户 / Agent 两部分
├── README.md                # 本文
├── CONTEXT.md               # 术语表
├── docs/adr/                # 关键决策记录
├── template/                # Typst 模板（构建时内联进产物）
│   ├── 00-util.typ          # 中文数字、页边距、纸张
│   ├── 20-frontmatter.typ   # 封面、文章标题块、目录、信函头尾、参考文献
│   ├── 30-blocks.typ        # 定理/定义/例题等语义块
│   ├── 32-code.typ          # 代码块与行号
│   ├── 35-notes.typ         # 边注（脚注可改排页边）
│   ├── 38-chess.typ         # 棋谱 import（只在用到时内联）
│   ├── 40-kinds.typ         # 小说章首、首字下沉
│   ├── 90-doc.typ           # 主装配
│   └── meta.typ             # pandoc 元数据模板
├── filters/features.lua     # 元数据驱动的重写：笔记模式、代码行号（先跑）
├── filters/refs.lua         # @fig: 交叉引用与 \eqref / \ref
├── filters/semantic.lua     # ::: div → 语义块；章首首段标记
├── filters/diagrams.lua     # 图表围栏 → figure（元数据驱动）
├── filters/chess.lua        # 棋谱围栏 → staunton 调用
├── vendor/typst-packages/   # 内联的 staunton 2.0.0（GPL 子目录，见 NOTICE）
├── scripts/build_pdf.py     # detect / build / style / check / doctor
├── test/                    # 无第三方依赖的测试
├── references/              # typography（规范）/ kinds / style-knobs / authoring / citations / chess / troubleshooting
└── examples/                # 七种 Kind 各一份样张
```

## 测试

```bash
python -m unittest discover -s test -v
```

缺失 typst 或 pandoc 时，端到端用例自动跳过。

## 已知限制

- **边注是浮动定位**：它贴在锚点那一行，不占垂直空间；两条锚得太近会重叠，构建时会警告（没有自动避让）。
- **`gb-7714-2015-numeric` 不显示页码定位**：`[@key, p. 33]` 在这个样式下只出编号；需要页码就用 `ieee` / `apa`。
- **棋谱的自动题注是英文**（`White to move`、`Position after 17. Rd8#`），中文文档只把编号前缀换成「棋图」。
- **图表要可选渲染器**：`dot` 来自 Graphviz、`mermaid` 要 `mmdc`；没装时图按源码排出并给警告，构建不失败。
- Typst 0.15 在段距接近 0 时会把下一段抬高半行，构建脚本据此把最小段距定为 4.5pt；书/小说因此有一点点段间距。
- **运行时不联网**：模板与 staunton 都在仓库里；只有手动 `typst compile` 棋谱文档时需要 `--package-path`。

## License

MIT，见 [LICENSE](LICENSE)。

