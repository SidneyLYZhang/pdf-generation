# Markdown 写法

解析器是 pandoc，方言为 **GFM + fenced_divs**（`-f gfm+fenced_divs`）。GFM 让「冒号后面的列表」不会被吞成一段，这一点比 pandoc 默认的 markdown 方言省心很多。

## 标题与结构

```markdown
# 一级标题（章）
## 二级标题（节）
### 三级标题
```

- 标题编号由 Kind 决定，**源代码里不要手写「1.1」「第一章」**，否则会重复编号。
- `book` / `textbook` / `novel` 的一级标题会自动另起一页。
- 想要不带标题的分页，用 `::: pagebreak :::`。

## 段落与列表

空行分段。列表、任务列表、嵌套列表：

```markdown
- 一级
  - 二级
1. 有序
- [ ] 未完成
- [x] 已完成
```

GFM 允许列表直接跟在段落行后面，不必空行；但为了源码可读，仍建议空行。

## 表格

```markdown
| 指标 | 本季 | 环比 |
|------|-----:|-----:|
| 新增 | 48.7 | +12% |
```

- 表头自动加粗、带分隔线；表格按内容宽度居中。
- 列特别多的表会变窄，必要时拆成两张表或减少列。
- 对齐用 `---:` / `:---` 控制，pandoc 会转成 Typst 的列对齐。

## 代码

````markdown
```python
print("hi")
```
````

带语言标记才有高亮和语言栏；没有标记的代码块也有底色，但不做语法高亮。代码块里的中文用中文字体兜底。

## 数学

行内 `$E = mc^2$`，行间 `$$...$$`。**两条硬规则**：

1. `$` 内侧不能有空格：`$ x $` 不会被识别成数学，会原样排出来。
2. 只用合法 LaTeX 命令：`\alpha`、`\frac{a}{b}`、`\ge`。`\/` 这类 LaTeX 排版指令会被 pandoc 判为非法并退化成纯文本，编译日志里会有 `Could not convert TeX math`。

pandoc 会把 LaTeX 数学翻译成 Typst 数学，例如 `\frac{a}{b}` → `a/b`、`\alpha` → `alpha`。

## 语义块（教材 / 笔记）

用 fenced div 标记，class 决定渲染成哪种块：

```markdown
::: {.theorem title="极限的唯一性"}
若数列收敛，则极限唯一。
:::

::: {.notice}
提示内容。
:::

::: pagebreak
:::
```

可用的 class：

| class | 渲染 | 编号 |
|-------|------|------|
| `theorem` / `definition` / `lemma` / `proposition` / `example` / `exercise` | 浅底 + 强调色左边线 | 共享连续编号 |
| `proof` | 不编号，末尾 ∎ | 否 |
| `notice` / `tip` | 「提示」块 | 否 |
| `warning` / `caution` | 「注意」块 | 否 |
| `pagebreak` | 强制分页 | — |

`title` 属性可选，显示在标签后面。不认识的 class 会退化成普通块，内容不丢。

## 图片

```markdown
![图 1：渠道效率](img/channels.png){width=70%}
```

- 路径相对 Markdown 文件。
- 没写 `width` 时用默认 82% 正文宽度。
- 图片找不到时 Typst 会报错并指出路径——先检查相对路径。

## 脚注与引用

```markdown
正文[^1]。

[^1]: 脚注内容。
```

块引用用 `>`，会渲染成左侧竖线的弱化引文。

## frontmatter 元数据

| 键 | 用途 |
|----|------|
| `kind` | 版式（等价于 `--kind`） |
| `title` / `subtitle` | 标题 / 副标题 |
| `author` | 作者；多个用 YAML 列表 |
| `org` | 机构（封面显示为「机构」） |
| `date` | 日期文本，原样显示，不做格式化 |
| `abstract` / `keywords` | 仅 `article` 使用 |
| `letter:` | 仅 `letter` 使用，见 [kinds.md](kinds.md) |

## 多文件

```bash
python scripts/build_pdf.py build book.md ch01.md ch02.md
```

- **第一个文件**的 frontmatter 决定元数据和 Kind；后面文件的 frontmatter 会被忽略。
- 每个文件通常以 `# 章名` 开头。
- 顺序按命令行顺序，不按文件名排序（避免 `10-` 排在 `2-` 前面）。

## 不该写的东西

- 不要手写目录、页码、页眉、章节编号——模板负责。
- 不要用 HTML 标签做版式（`<div style=...>` 会被当普通文本）。
- 不要在正文里写 `#pagebreak()` 之类的 Typst 代码——pandoc 会把 `#` 当普通字符转义；用 `::: pagebreak :::`。
