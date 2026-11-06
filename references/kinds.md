# Kind 一览

Kind 决定「整份文档长什么样」：纸张、封面、目录、编号、分页规则、页眉页码、段落风格。七种 Kind 共享同一套模板代码，只是默认旋钮不同；任何默认都能被 Style spec 覆盖。

## report（默认）

- A4，封面（标题 / 副标题 / 报告人 / 机构 / 日期），目录 2 级，标题 `1.1` 编号，页眉显示文档标题，页脚居中页码。
- 段落：段间距 1em、无首行缩进——适合阅读型报告而不是书。
- 什么时候用：运营报告、项目总结、分析报告、白皮书初稿。
- 注意：`org` 字段会显示成「机构」；没有 `date` 时封面少一行，不会报错。

```bash
python scripts/build_pdf.py build report.md
```

## article

- A4，无封面；首页是标题块（标题 / 副标题 / 作者 / 机构 / 日期）+ 摘要 + 关键词，然后直接进正文。
- 摘要来自 frontmatter 的 `abstract`（支持多段），关键词来自 `keywords`。
- 默认不分章，`heading.page-break-before=true` 可让一级标题另起一页（长文的做法）。
- 什么时候用：单篇论文式文章、公众号长文、技术随笔。

```yaml
---
kind: article
title: "把留存拆成可干预的动作"
abstract: |
  第一段摘要。

  第二段摘要。
keywords: [留存, 实验]
---
```

## letter

- A4，无目录、无标题编号、无页码；页边距 3cm，段距 1.2em。
- 结构：右上发件人与日期 → 收件人 → 主题（加粗）→ 称呼 → 正文（Markdown）→ 右下敬语/署名/日期。
- 字段写在 frontmatter 的 `letter:` 下，字符串里的 `\n` 会被渲染成换行。
- 正文就是普通 Markdown 段落，不要手写「此致敬礼」块——用 `closing` 和 `signature`。

```yaml
---
kind: letter
date: "2026 年 11 月 6 日"
letter:
  from: "示例公司 · 示例部门\n示例市示例区示例路 88 号"
  to: "致：示例机构 · 数据合作组\n李四 先生"
  subject: "关于第四季度数据接口联调安排的函"
  salutation: "李四先生，您好："
  closing: "顺颂商祺"
  signature: "张三\n示例部门 负责人"
---
```

## note

- A4，紧凑：10.5pt、行距 0.6em、段距 0.5em、无封面无目录，页码靠右。
- 语义块默认可用（`theorem` / `notice` / `warning` 等），适合学习笔记、实验记录。
- 标题不编号；需要编号可以 `--set heading.numbering=1.1`。

## book

- 6×9 英寸（152×229mm），封面（书名 / 副标题 / 作者 / 机构 / 日期），目录 2 级，章起新页。
- 页眉奇偶交替：偶数页显示书名，奇数页显示当前章名；页码在切口侧。
- 段落：首行缩进 2em、段距 0.45em（Typst 0.15 的最小安全值），中文书籍观感。
- 多文件：每个 `.md` 是一章，第一个文件放 frontmatter。

```bash
python scripts/build_pdf.py build book.md ch01.md ch02.md
```

## textbook

- A4，封面（「编者」标签），目录 3 级，标题 `1.1.1` 编号，章起新页，页眉「章名 + 节名」。
- 语义块全开：定理、定义、引理、命题、例题、习题共用一个连续编号；`proof` 不编号、末尾带 ∎。
- 为什么适合教材：例题/习题/定理的视觉区分（浅底 + 强调色左边线）与编号是教材的核心。

```markdown
::: {.definition title="留存"}
……
:::

::: {.theorem title="留存与样本量"}
……
:::

::: {.exercise}
……
:::
```

## novel

- A5（148×210mm），封面（极简：书名 / 作者 / 一条短色线），目录仅章。
- 每章自动生成「第 N 章」前缀（中文数字），章名居中，下方一条短横线。
- 章首首段自动首字下沉（2.5 倍字号，占两行），其余段落首行缩进 2em、段距 0.45em。
- 首字下沉只处理纯文本首段；首段含行内标记（粗体/链接）时会退化成普通段落，不丢内容。

```yaml
---
kind: novel
title: "长夜里的信号"
author: "王二麻"
---
```

## 改动任一 Kind 的默认值

不用改模板，写进 `doc.yml` 或 `--set` 即可：

```bash
# 书稿改成 A4、加标题编号
python scripts/build_pdf.py build book.md --set page.paper=a4 --set heading.numbering=1.1

# 报告换成整版色封面 + 靛蓝配色
python scripts/build_pdf.py build report.md --set cover.style=full --set color.palette=indigo
```
