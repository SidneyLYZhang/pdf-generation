# Markdown 写法

解析器是 pandoc，方言为 **GFM + fenced_divs**（`-f gfm+fenced_divs`）。GFM 让「冒号后面的列表」直接成列表，省掉一类历史遗留的排版事故。

## 标题与结构

```markdown
# 一级标题（章）
## 二级标题（节）
### 三级标题
```

章节编号由模板按 Kind 生成。正文里写纯标题文字，编号、目录、页眉都会自动对齐。

需要不带标题的分页时，用 `::: pagebreak :::`。

## 段落与列表

空行分段。嵌套列表、任务列表都按 GFM 解析：

```markdown
- 一级
  - 二级
1. 有序
- [ ] 未完成
- [x] 已完成
```

## 表格

```markdown
| 指标 | 本季 | 环比 |
|------|-----:|-----:|
| 新增 | 48.7 | +12% |
```

表头自动加粗并带分隔线；列对齐用 `---:` / `:---`。列多的宽表会挤，拆成两张表或删列更合适。

## 代码

````markdown
```python
print("hi")
```
````

带语言标记才有高亮和顶部语言栏。代码块的等宽字体用 DejaVu Sans Mono，中文自动回退。

## 数学

行内 `$E = mc^2$`，行间 `$$...$$`。两条硬规则：

1. `$` 内侧紧贴内容：`$x$` 是数学，`$ x $` 会被当普通文本原样排出。
2. 用合法 LaTeX 命令：`\alpha`、`\frac{a}{b}`、`\ge`。`\/` 这类排版指令不是合法数学，pandoc 会打印 `Could not convert TeX math` 并降级成纯文本。

pandoc 负责把 LaTeX 翻成 Typst 数学：`\frac{a}{b}` → `a/b`，`\alpha` → `alpha`。

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

| class | 渲染 | 编号 |
|-------|------|------|
| `theorem` / `definition` / `lemma` / `proposition` / `example` / `exercise` | 浅底 + 强调色左边线 | 共享连续编号 |
| `proof` | 不编号，末尾 ∎ | 否 |
| `notice` / `tip` | 「提示」块 | 否 |
| `warning` / `caution` | 「注意」块 | 否 |
| `pagebreak` | 强制分页 | — |

`title` 属性可选，显示在标签后面。不认识的 class 会渲染成普通块，内容保留。

## 图片

```markdown
![图 1：渠道效率](img/channels.png){width=70%}
```

- 路径相对 Markdown 文件。
- 省略 `width` 时用 `float.figure-width` 的默认值（82%）。
- 图片找不到时 Typst 会报错并打印解析后的路径，先查相对路径。

## 脚注与引用

```markdown
正文[^1]。

[^1]: 脚注内容。
```

`>` 块引用会渲染成左侧竖线的弱化引文。

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

- **第一个文件**的 frontmatter 决定元数据和 Kind。
- 每个文件通常以 `# 章名` 开头。
- 章序按命令行顺序，与文件名无关。

## 交给模板处理的部分

目录、页码、页眉、章节编号、图表编号都由模板生成；源码里写内容本身即可。HTML 标签会被当作普通文本；Typst 代码（如 `#pagebreak()`）会被转义，分页用 `::: pagebreak :::`。
