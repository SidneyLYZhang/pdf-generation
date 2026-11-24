---
name: pdf-generation
description: 把 Markdown 排成 PDF（Typst 排版，不装 LaTeX）：报告、白皮书、信函、书稿、教材、小说、笔记。当用户要把 .md 转成 PDF、按某种文档类型排版、或调整已有 PDF 的版式与观感时使用。
---

# PDF Generation

pandoc 把 Markdown 解析成 Typst 源码（`-f` 默认是钉死的 pandoc markdown 扩展串，见 `--from`），版式由本 skill 自带的模板承担，`typst` 直接渲染 PDF。七种 Kind、一个 Style spec、一条固定流程。

流程六步；每一步末尾的完成判据不成立，就不进入下一步。

## 1. 扫描

```bash
python scripts/build_pdf.py detect <输入文件...>
```

拿到 JSON：`suggested_kind`、`lang`、字数、标题层级、frontmatter 键，以及 `features` 里的特征位（表格、代码、公式、图片、引文、交叉引用、边注、图表、棋谱……）。

**完成判据**：你能说出建议 Kind、语言，以及 JSON 里 `features` 为 `true` 的每一项打算怎么排（引文用哪套样式、图表交给哪个渲染器、棋谱用哪种围栏）。

## 2. Clarify：只问会改变成品的选择

一轮问完，最多 8 个问题；每题给 2–4 个选项、一个**推荐值**和一句理由；末尾附「全部按推荐」。

| # | 问题 | 何时问 | 推荐值 |
|---|------|--------|--------|
| 1 | Kind | 检测结果与内容有歧义 | `detect` 的 `suggested_kind` |
| 2 | 语言 / 字体 | 中英混排且用户没提 | 正文含中文 → 中文预设；纯英文 → 英文预设 |
| 3 | 纸张 | 用户没提且不是书稿 | 见下表默认纸张 |
| 4 | 封面元信息 | 要做封面但缺报告人/机构/日期 | 从 frontmatter 补；缺的留空，交付时说明 |
| 5 | 配色 | 用户没提 | `teal`；正式场合用 `mono` |
| 6 | 代码行号 | 源文件含代码块且用户没提 | 不加行号（`code.line-numbers=false`）；要引用具体行时再加 |
| 7 | 引文样式 | `detect` 报 `citation: true`，或用户提到参考文献 | 按语言默认：中文 GB/T 7714、英文 IEEE、`article` 用 APA |
| 8 | 边注 | 脚注较多，或 Kind 是 `textbook` | `textbook` 用页边；其余保持页脚 |

字号、行距、页边距、目录深度、代码主题留到第 6 步，第一版一律用 Kind 默认值。

三类答案直接沿用，不再发问：frontmatter 里已有的元数据、用户消息里已经说过的、以及 `detect` 能确定的事实。

Kind 与内容明显匹配时（frontmatter 已有 `letter:` 字段、一级标题构成多章书稿），走**声明式自动确认**：说一句「我按 letter / A4 / 无目录 排」，直接进入第 3 步，不停下来等回复。用户想改会自己说。

用户说「你定 / 随便 / 看着办」：整轮跳过，全部取推荐值。

有结构化提问工具就用（DSH 的 `ask_user_question`、Claude Code 的 `AskUserQuestion`），没有就把问题写成编号文本。

**完成判据**：每个不确定项都有答案（问到的，或明确取默认的），并且你能写出一句「按 X Kind、Y 纸张、Z 配色生成」。

## 3. 落 Spec

把与默认不同的答案写进 `<首个输入文件同名>.doc.yml`：

```yaml
kind: report
style:
  color:
    palette: indigo
  page:
    margin: 2.4cm
```

`kind` 也可以写在 Markdown frontmatter 里。全部取默认时跳过本步。

**完成判据**：`doc.yml` 已存在，或你确认本轮全部使用默认值。

## 4. 生成

```bash
python scripts/build_pdf.py build <输入文件...> [-o out.pdf] [--kind K] [--doc spec.yml] [--set key=value ...]
```

多文件（书 / 教材 / 小说）：第一个文件管元数据，每个文件一章，章序按命令行顺序：

```bash
python scripts/build_pdf.py build book.md ch01.md ch02.md
```

产物三件：`<stem>.pdf`（交付）、`<stem>.typ`（自包含；手工编译用文件头那行现成命令，需要时带 `--root` / `--package-path`）、`<stem>/` 下的抽页 PNG。

**完成判据**：命令退出码为 0，且输出里有 `PDF ... (N 页)`。

## 5. 抽页目检

用读图能力打开构建打印出的 PNG。默认抽文档中部的一页正文；出现 warning（缺字体、内容溢出）时自动多抽封面和前几页。

看三件事：字体是否成方块、表格/代码是否溢出、封面与目录是否错位。文档里有**棋谱、图表、边注、行号**时，对应那页要单独看一眼：棋盘有没有缺子、图表是否被裁、边注有没有压住正文。

```bash
python scripts/build_pdf.py build doc.md --check all   # 全量逐页
python scripts/build_pdf.py build doc.typ              # 只查已有 .typ
```

**完成判据**：你看过至少一张抽页，并能说出上面三件事各自的状态；文档里有棋谱、图表、边注或行号时，对应那页也看过。

## 6. 调整

用户说「标题太大 / 页边距再宽点 / 换个配色」时，改旋钮，不动正文。优先级从高到低：`--set` > `<stem>.doc.yml` > Kind 默认 > 全局默认；Markdown frontmatter 只提供元数据（标题、作者、`kind`、书目等）。

```bash
python scripts/build_pdf.py style doc.md --write doc.doc.yml   # 导出完整 spec
python scripts/build_pdf.py build doc.md --set heading.size-1=18pt --set color.palette=sepia
```

**完成判据**：新 PDF 已生成，且第 5 步的抽页重新看过一遍。

## Kind 速查

| Kind | 用于 | 默认纸张 |
|------|------|----------|
| `report` | 运营/项目/分析报告（默认） | A4 |
| `article` | 单篇文章、论文式长文 | A4 |
| `letter` | 公函、商务信函 | A4 |
| `note` | 学习/实验笔记，紧凑排版 | A4 |
| `book` | 书稿、白皮书 | 6×9 |
| `textbook` | 教材：定理/例题/习题 | A4 |
| `novel` | 小说：第 N 章、首字下沉 | A5 |

每种 Kind 的封面、目录、编号、页眉细节在 [references/kinds.md](references/kinds.md)。

## 内容速查

正文里能写什么，按「想排成什么」查：

| 想排 | 写法 |
|------|------|
| 引文 + 参考文献 | frontmatter `bibliography: references.bib`，正文 `[@key]` |
| 交叉引用 | `{#fig:x}` + `@fig:x`；公式 `\label{eq:x}` + `\eqref{}` / `@eq:` |
| 边注 | `[文字]{.sidenote}` 或 `::: {.sidenote}` |
| 代码行号 | `--set code.line-numbers=true`，或单块 `{.line-numbers}` |
| 图表 | ```` ```dot ```` / ```` ```mermaid ```` 围栏 |
| 公式编号 | 自动（book/article）或 `--set math.numbering=(1)` |
| 棋谱 | ```` ```fen ```` / ```` ```pgn ```` / ```` ```notation ```` |

引文细节见 [references/citations.md](references/citations.md)，棋谱见 [references/chess.md](references/chess.md)，其余见 [references/authoring.md](references/authoring.md)。

## 参考

按需读取，不必预先加载：

- [references/typography.md](references/typography.md) — 排版原则的规范：两档规则、口径、场景映射、偏离写法；动版式之前先读这份
- [references/style-knobs.md](references/style-knobs.md) — 全部旋钮、取值格式、各 Kind 覆盖表
- [references/troubleshooting.md](references/troubleshooting.md) — 报错与版式问题的处理
- [INSTALL.md](INSTALL.md) — 安装（分「用户」与「Agent」两部分）

Kind 速查与内容速查已经链到 kinds、authoring、citations、chess 四份文档。
