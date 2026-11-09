# Markdown 写法

解析器是 pandoc，方言是一条钉死的 pandoc markdown 扩展串（`scripts/build_pdf.py` 里的 `FROM_FORMAT`，可用 `--from` 覆盖）。它保留了 GFM 的手感——「冒号后面的列表」仍然直接成列表，同时打开引文、属性与图片题注。

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

行号默认不开。要整篇开：`--set code.line-numbers=true`；只给某一块：

````markdown
```python {.line-numbers}
def f(x):
    return x
```
````

整篇开了之后想让某一块不要行号，用 `{.no-line-numbers}`。行号按块从 1 数起，跨页不断号；行内代码永远不带行号。

## 数学

行内 `$E = mc^2$`，行间 `$$...$$`。两条硬规则：

1. `$` 内侧紧贴内容：`$x$` 是数学，`$ x $` 会被当普通文本原样排出。
2. 用合法 LaTeX 命令：`\alpha`、`\frac{a}{b}`、`\ge`。`\/` 这类排版指令不是合法数学，pandoc 会打印 `Could not convert TeX math` 并降级成纯文本。

pandoc 负责把 LaTeX 翻成 Typst 数学：`\frac{a}{b}` → `a/b`，`\alpha` → `alpha`。

**公式编号**：`book` 与 `article` 默认给行间公式编号（`(1)`），其余 Kind 默认不编号；`--set math.numbering=(1)` 打开，`none` 关掉。

**交叉引用**：公式里写 `\label{eq:x}`，正文用 `\eqref{eq:x}`、`\ref{eq:x}` 或 `@eq:x` 引用，三者等价（标签与引用的通用规则见上面的「交叉引用」）。公式没编号时引用会直接报错——先打开 `math.numbering`。

### 转换审计

常见写法的实测结果；标了现象的才需要改写法：

| 写法 | 结果 |
|------|------|
| `\frac` `\sqrt` `\sum` `\int` `^` `_` | 正常 |
| `aligned` `cases` | 正常（`&` 对齐点保留） |
| `\text{中文}` | 正常，排成直立文字 |
| `\mathrm` `\mathbb` `\operatorname` | 正常 |
| `\vec` `\hat` `\cdot` | 正常 |
| `\,` `\;` `\quad` `\qquad` | 正常（thin / thick / 1em / 2em 空格） |
| `\mathbf{x}` | 变成直立粗体，不是粗斜体；介意就手写 Typst 数学 |
| `\tag{...}` | 静默丢弃；编号由模板统一给 |
| `\nonumber` | 被吞掉，公式**照常编号**（没法只给某一条公式去编号） |
| `\notag` | **整条公式退回字面文本**，PDF 里能看到 `$$` |
| 裸的 `\begin{equation}` / `\begin{align}` / `\begin{gather}` | **整段变成字面文本**；改写 `$$\begin{aligned}…\end{aligned}$$` |

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

## 图表（mermaid / graphviz）

`mermaid` 与 `dot`（Graphviz）围栏在构建时渲染成 SVG，变成带编号的图：

````markdown
```dot {#fig:flow caption="数据采集流程" width=70%}
digraph G { rankdir=LR; 采集 -> 清洗 -> 入库; }
```
````

- 选项写在围栏的 `{…}` 里：`caption`（题注）、`width`（`60%` / `10cm`）、`#fig:xxx`（标签，供 `@fig:` 引用）。
- 渲染结果按内容 hash 缓存在源文件旁的 `.pdfgen/diagrams/`，同样的图不会重复渲染。
- 没装渲染器时构建照常成功：给一条警告，图按源码排出；若写了 `caption` 或 `#fig:`，仍会包成 figure（源码在图内），编号和 `@fig:` 引用照常成立。`dot` 来自 Graphviz，`mmdc` 来自 `npm i -g @mermaid-js/mermaid-cli`。
- 渲染失败（语法错）会终止构建，报错里带文件和围栏起始行。
- 图与普通图片共用 `float.*` 旋钮（题注位置、编号格式、默认宽度）。

## 图片

```markdown
![渠道效率](img/channels.png){width=70%}
```

- 单独成段的图片会变成带题注的 figure，题注取 alt 文字；编号（「图 1」）由模板自动加，**alt 里不要再写「图 1：」**，否则会出现「图 1 图 1：渠道效率」。
- `{width=70%}` 控制宽度；省略时用 `float.figure-width` 的默认值（82%）。
- 路径相对 Markdown 文件。
- 图片找不到时 Typst 会报错并打印解析后的路径，先查相对路径。

## 脚注与块引用

```markdown
正文[^1]。

[^1]: 脚注内容。
```

`>` 块引用会渲染成左侧竖线的弱化引文。

## 边注

注释可以排到页边，而不是页脚：

```markdown
正文里的一条边注[这条会出现在页边。]{.sidenote}。

::: {.sidenote}
块级边注，独占一行的注释。
:::
```

- 行内用 span、块级用 div，**类名都是 `.sidenote`**。
- 只要出现显式标记，文档自动切到边注模式：外侧页边加宽，正文宽度相应减小。只有你显式设了 `note.style=footnote` 时才不切——那时边注退化成脚注（优先级 `--set` > frontmatter > doc.yml）。
- 想让普通脚注也走页边：`--set note.style=margin`（`textbook` 默认就是 margin）；默认 `footnote`，脚注留在页脚。
- 旋钮：`note.width`（边注栏宽，默认 4.2cm）、`note.gap`（与正文的间距，12pt）、`note.size`（8pt）。
- 边注是**浮动定位**：贴在锚点那一行，不占垂直空间。两条边注挨太近会重叠，构建时会警告；单条超过 200 字也会警告——那种长度更适合脚注。
- 设了装订线（`page.gutter`）时按双面排版处理，偶数页的边注落在左侧。

## 引文与书目

在 frontmatter 声明书目文件，正文用 `[@key]` 标注引文：

```yaml
---
title: 报告
bibliography: refs.bib
---
```

```markdown
已有研究指出[@doe2020]，另一项工作给出了不同结论[@smith2021]。
带页码定位：[@doe2020, p. 33]。
```

- 数据文件支持 `.bib`（BibTeX）、`.json`（CSL-JSON）、`.yml`（Hayagriva），路径相对 Markdown。
- `cite.enabled` 默认 `auto`：声明了 `bibliography` 才生成参考文献表；想关掉设成 `false`。
- 默认样式：中文 `gb-7714-2015-numeric`，英文 `ieee`，`article` 用 `apa`。换成内置样式名或 `.csl` 路径：`--set cite.style=apa`、`cite.style: vancouver`。
- 标题默认「参考文献 / References」，进目录；`cite.title` 可改。
- 缺书目文件、缺 key 都会让构建失败并指出名字，不会静默排出裸 key。
- 坑：`gb-7714-2015-numeric` 不显示页码定位（CSL 实现所限），需要页码就用 `ieee` / `apa`，或把页码写进正文。

## 交叉引用

给图、表、公式、节打标签，正文用 `@` 标注指向它们：

```markdown
# 方法 {#sec:method}

![渠道效率](img/channels.png){#fig:channels}

: 槽位表 {#tab:slots}

| 渠道 | 槽位 |
|------|-----:|

$$ y = mx + b \label{eq:line} $$

见图 @fig:channels、表 @tab:slots、式 @eq:line，见 @sec:method。
```

- 保留前缀只有四个：`fig:` `tab:` `eq:` `sec:`。**其余 `@id` 一律当引文**，所以书目 key 别用这四个前缀。
- 编号文字由 Typst 生成（「图 1」「表 1」「式 1」「小节 1」），不要在正文里手写。
- 指向不存在的 id 会构建失败并打印那个 id。
- 公式必须先有编号才能被指向：`math.numbering` 为 `none` 时会直接报错，用 `--set math.numbering=(1)` 打开。

## frontmatter 元数据

| 键 | 用途 |
|----|------|
| `kind` | 版式（等价于 `--kind`） |
| `title` / `subtitle` | 标题 / 副标题 |
| `author` | 作者；多个用 YAML 列表 |
| `org` | 机构（封面显示为「机构」） |
| `date` | 日期文本，原样显示，不做格式化 |
| `bibliography` | 书目文件路径（`.bib` / CSL-JSON / Hayagriva），见「引文与书目」 |
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
