---
name: pdf-generation
description: 把 Markdown 排成专业 PDF。pandoc 解析、Typst 排版，支持报告、文章、信函、笔记、书、教材、小说七种 Kind，样式可按文档逐项调整。当用户要求把 .md 转成 PDF、要做白皮书/信函/书稿/教材、或对已有 PDF 的版式不满意要调整时使用。
---

# PDF Generation

Markdown 进来，PDF 出去。pandoc 只负责把 Markdown 解析成 Typst 源码，版式全部由本 skill 自带的 Typst 模板决定，最后由 `typst` 直接渲染 PDF——不经过 LaTeX。

## 流程（按顺序走，不要跳步）

```
detect  →  clarify  →  <stem>.doc.yml  →  build  →  目检抽页  →  按反馈调整
```

### 1. 先扫描，再决定问什么

```bash
python scripts/build_pdf.py detect <输入文件...>
```

输出 JSON，含建议 Kind、语言、字数、标题数、是否含表格/代码/公式/图片/frontmatter 键。**先跑它，不要凭文件名猜。**

### 2. Clarify：只问会改变成品的

原则：

- 一轮问完，**最多 5 个**，按下面的优先级取。
- 每个问题给 2–4 个选项 + **推荐值** + 一句理由。末尾给「全部按推荐」。
- 已有答案的不问：frontmatter 里写了作者/日期、用户消息里说了「A4」，就别再问。
- **声明式自动确认**：Kind 与内容明显匹配时（例如 frontmatter 已有 `letter:` 字段、标题层级显示是多章书稿），不要停下来等确认，直接说一句「我按 letter 排，A4，无目录」然后开始生成；用户想改会自己说。
- 用户说「你定 / 随便 / 看着办」→ 整轮跳过，全部用推荐值。
- 有结构化提问工具就用（DSH 的 `ask_user_question`、Claude Code 的 `AskUserQuestion`）；没有就用编号文本。

优先级与推荐：

| # | 问题 | 何时问 | 推荐 |
|---|------|--------|------|
| 1 | Kind | 检测结果与内容有歧义 | `detect` 的 `suggested_kind` |
| 2 | 语言 / 字体 | 中英混排且用户没提 | 正文有中文 → 中文预设；纯英文 → 英文预设 |
| 3 | 纸张 | 没人提且不是书稿 | report/article/note/letter/textbook 用 A4；book 用 6×9；novel 用 A5 |
| 4 | 封面元信息 | 要做封面但缺报告人/机构/日期 | 从 frontmatter 补；缺失就留空并在交付时说明 |
| 5 | 配色 | 用户没提 | `teal`；正式场合可 `mono` |

不要问：字号、行距、页边距、目录深度、代码主题——这些是「调整阶段」的事，先按 Kind 默认出第一版。

### 3. 把答案写进 Style spec

`<首个输入文件同名>.doc.yml`，**只写非默认项**：

```yaml
kind: report
style:
  color:
    palette: indigo
  page:
    margin: 2.4cm
```

`kind` 也可以直接写在 Markdown frontmatter 里。完整旋钮见 [references/style-knobs.md](references/style-knobs.md)。

### 4. 生成

```bash
python scripts/build_pdf.py build <输入文件...> [-o out.pdf] [--kind K] [--doc spec.yml] [--set key=value ...]
```

多文件（书/教材/小说）：第一个文件管元数据，每个文件是一章：

```bash
python scripts/build_pdf.py build book.md ch01.md ch02.md
```

产物：

- `<stem>.pdf` — 交付物
- `<stem>.typ` — **自包含**中间件（模板已内联），可直接 `typst compile <stem>.typ` 复现；每次 build 会覆盖，直接改它请按「先 build、手改、再 `build <stem>.md --keep-typ`」的顺序来
- `<stem>/` 下的 PNG — 自检抽页

### 5. 目检一页，别只看有没有报错

`build` 默认抽 1 页（文档中部的正文页）渲染成 PNG，路径会打印出来。**用读图能力真的看一眼**：字体是否变成方块、表格是否溢出、封面/目录是否错位。出现 warning（缺字体、内容溢出）时会自动多抽封面和前几页。

```bash
python scripts/build_pdf.py build doc.md --check all   # 全量逐页
python scripts/build_pdf.py check doc.typ              # 只重查已有 .typ
```

### 6. 用户要改排版时

优先级从高到低：`--set` > Markdown frontmatter（元数据）> `<stem>.doc.yml` > Kind 默认 > 全局默认。

```bash
python scripts/build_pdf.py style doc.md --write doc.doc.yml   # 导出当前完整 spec
python scripts/build_pdf.py build doc.md --set heading.size-1=18pt --set color.palette=sepia
```

改完重新 build，再抽页看一次。用户说「标题太大」「页边距再宽一点」时，改对应的旋钮，不要把整份 Markdown 重写。

## Kind 一览

| Kind | 纸张 | 封面 | 目录 | 标题编号 | 分章 | 典型用途 |
|------|------|------|------|----------|------|----------|
| `report` | A4 | 有（报告人/机构/日期） | 有 | 1.1 | 否 | 默认；运营/项目/分析报告 |
| `article` | A4 | 无（首页标题块+摘要） | 无 | 1.1 | 可选 | 单篇文章、论文式长文 |
| `letter` | A4 | 无 | 无 | 无 | 否 | 公函、商务信函 |
| `note` | A4 | 无 | 无 | 无 | 否 | 学习/实验笔记，紧凑排版 |
| `book` | 6×9 | 有 | 有 | 1.1 | 是 | 书稿、白皮书 |
| `textbook` | A4 | 有 | 有（3 级） | 1.1.1 | 是 | 教材，含定理/例题/习题 |
| `novel` | A5 | 有 | 有（仅章） | 第 N 章 | 是 | 小说，章首装饰 + 首字下沉 |

细节与逐 Kind 的默认值见 [references/kinds.md](references/kinds.md)。

## Markdown 约定

- 方言是 GFM（`pandoc -f gfm+fenced_divs`）。冒号后的列表、任务列表、脚注、管道表格都直接支持。
- **数学**：行内 `$x$`、行间 `$$...$$`，`$` 内侧不要留空格（`$ x $` 不会被识别）；LaTeX 命令照常用 `\alpha`、`\frac`，pandoc 会转成 Typst 数学。
- **语义块**（教材、笔记尤其常用）：

  ```markdown
  ::: {.theorem title="极限的唯一性"}
  若数列收敛，则极限唯一。
  :::

  ::: {.notice} 提示内容 :::   ::: pagebreak :::
  ```

  可用 class：`theorem` `definition` `lemma` `proposition` `example` `exercise` `proof` `notice` `warning`；`pagebreak` 强制分页。
- **信函**：frontmatter 里写

  ```yaml
  letter:
    from: "公司名\n地址"
    to: "致：某某"
    subject: "关于……的函"
    salutation: "某某先生，您好："
    closing: "顺颂商祺"
    signature: "姓名\n部门"
  ```

- **图片**：相对 Markdown 的路径，`![图注](img/x.png){width=60%}`。
- **多文件**：见上，第一个文件的 frontmatter 管标题/作者/日期。

更多写法与坑见 [references/authoring.md](references/authoring.md)。

## 排错

先跑 `python scripts/build_pdf.py doctor`：检查 pandoc/typst 版本、内置字体、中文字体、模板自检。常见错误与处理见 [references/troubleshooting.md](references/troubleshooting.md)。

## 边界

- 不做参考文献/引文管理（v1 没有 `bibliography`）。
- 不做边注、代码行号。
- Typst 0.15 在段距接近 0 时会把下一段抬高半行，所以段距小于 4.5pt 会被自动抬到 4.5pt——书/小说因此有一点点段间距，不要试图改成 0。
- 不联网拉 Typst 包；模板全部内置。
