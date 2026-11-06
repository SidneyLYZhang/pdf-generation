# Style spec 旋钮

一个文档的排版由一份 Style spec 决定。它是 `doc.yml` 里 `style:` 的内容，构建时与 Kind 默认合并成完整取值。

## 优先级

从高到低：

1. `--set key=value`（一次性覆盖）
2. Markdown frontmatter（只影响元数据：标题、作者、日期、机构、letter 字段）
3. `<首个输入文件>.doc.yml` 的 `style:`
4. Kind 默认值
5. 全局默认值

未知 key 会直接报错，并给出最接近的合法项。

## 全局默认

| 旋钮 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page.paper` | paper | `a4` | 纸张：a4 / a5 / 6x9 / letter |
| `page.margin` | length | `2.5cm` | 四边页边距 |
| `page.gutter` | length | `0cm` | 装订线（内侧额外留白） |
| `text.font` | fontlist | `auto` | 正文字体栈，按顺序取字形 |
| `text.heading-font` | fontlist | `auto` | 标题字体栈 |
| `text.size` | length | `11pt` | 正文字号 |
| `text.leading` | length | `0.65em` | 行距（行与行之间的额外距离） |
| `text.paragraph-spacing` | length | `1em` | 段间距；小于 4.5pt 会被抬到 4.5pt（Typst 0.15 限制） |
| `text.first-line-indent` | length | `0em` | 段首缩进，中文书籍习惯 2em |
| `text.justify` | bool | `true` | 两端对齐 |
| `text.hyphenate` | bool | `true` | 西文断词 |
| `text.lang` | str | `auto` | 语言标签，zh / en / auto |
| `heading.size-1` | length | `20pt` | 一级标题字号 |
| `heading.size-2` | length | `14pt` | 二级标题字号 |
| `heading.size-3` | length | `11.5pt` | 三级标题字号 |
| `heading.color` | color | `auto` | 标题颜色 |
| `heading.numbering` | numbering | `1.1` | 标题编号格式：1.1 / 1.a / none |
| `heading.page-break-before` | bool | `false` | 一级标题是否另起一页 |
| `heading.space-before` | length | `1.6em` | 标题上方留白 |
| `heading.space-after` | length | `0.7em` | 标题下方留白 |
| `heading.rule` | bool | `false` | 一级标题下是否加细线 |
| `color.palette` | palette | `teal` | 配色：teal / indigo / sepia / mono |
| `color.accent` | color | `auto` | 强调色（色带、语义块边线、链接默认值） |
| `color.ink` | color | `auto` | 正文颜色 |
| `color.muted` | color | `auto` | 次要文字颜色（页眉、题注、日期） |
| `color.rule` | color | `auto` | 细线颜色 |
| `color.link` | color | `auto` | 链接颜色 |
| `color.code-bg` | color | `auto` | 代码块底色 |
| `color.tint` | color | `auto` | 语义块与摘要底色 |
| `furniture.header` | header | `auto` | 页眉：none / title / book（奇偶交替）/ chapter |
| `furniture.header-rule` | bool | `true` | 页眉下细线 |
| `furniture.page-number` | pagenumber | `auto` | 页码位置：none / footer-center / footer-right / footer-outside |
| `furniture.page-number-format` | str | `1` | 页码格式，Typst numbering 写法，如 1 / a / i |
| `cover.enabled` | bool | `auto` | 是否生成封面 |
| `cover.style` | coverstyle | `auto` | 封面样式：band（色带）/ full（整版色）/ minimal（极简） |
| `cover.tagline` | str | `` | 封面上的短句 |
| `cover.logo` | str | `` | 封面 logo 图片路径 |
| `toc.enabled` | bool | `auto` | 是否生成目录 |
| `toc.depth` | int | `auto` | 目录深度（标题层级） |
| `toc.title` | str | `auto` | 目录标题文字 |
| `float.figure-caption` | captionpos | `bottom` | 图片题注位置：top / bottom |
| `float.table-caption` | captionpos | `top` | 表格题注位置：top / bottom |
| `float.numbering` | numbering | `1` | 图表编号格式，如 1 / (1) / none |
| `float.figure-width` | ratio | `82%` | 图片默认宽度（占正文宽度） |
| `code.theme` | codetheme | `default` | 代码高亮：default / none |
| `code.size` | length | `9pt` | 代码字号 |
| `code.header` | bool | `true` | 代码块顶部语言栏 |
| `math.numbering` | numbering | `none` | 公式编号格式，如 1 / (1) / none |
| `semantic.numbering` | numbering | `1` | 语义块编号格式，如 1 / (1)；none 表示只显示标签不编号 |
| `novel.dropcap` | bool | `auto` | 章首首字下沉 |
| `novel.chapter-prefix` | bool | `auto` | 自动生成「第 N 章」前缀 |

## 各 Kind 的覆盖

只列出与该 Kind 的全局默认不同的项；其余沿用上表。

| 旋钮 | report | article | letter | note | book | textbook | novel |
|------|------|------|------|------|------|------|------|
| `cover.enabled` | `True` | `False` | `False` | `False` | `True` | `True` | `True` |
| `cover.style` | `band` | — | — | — | `band` | `band` | `minimal` |
| `furniture.header` | `title` | `none` | `none` | `none` | `book` | `chapter` | `none` |
| `furniture.page-number` | `footer-center` | `footer-center` | `none` | `footer-right` | `footer-outside` | `footer-outside` | `footer-center` |
| `heading.numbering` | `1.1` | `1.1` | `none` | `none` | `1.1` | `1.1.1` | `none` |
| `heading.page-break-before` | `False` | `False` | `False` | `False` | `True` | `True` | `True` |
| `heading.rule` | `False` | — | `False` | — | `True` | `True` | `False` |
| `heading.size-1` | `22pt` | `19pt` | `14pt` | `17pt` | `22pt` | `22pt` | `20pt` |
| `heading.size-2` | — | — | — | — | `15pt` | `15pt` | — |
| `heading.size-3` | — | — | — | — | `12pt` | `12pt` | — |
| `novel.chapter-prefix` | — | — | — | — | `False` | `False` | `True` |
| `novel.dropcap` | — | — | — | — | `False` | `False` | `True` |
| `page.margin` | — | — | `3cm` | — | `2cm` | `2.4cm` | `2.2cm` |
| `page.paper` | — | — | — | — | `6x9` | `a4` | `a5` |
| `semantic.numbering` | `none` | — | — | — | — | `1` | — |
| `text.first-line-indent` | `0em` | `0em` | `0em` | `0em` | `2em` | `2em` | `2em` |
| `text.leading` | — | — | — | `0.6em` | — | — | — |
| `text.paragraph-spacing` | `1em` | `0.9em` | `1.2em` | `0.5em` | `0.45em` | `0.35em` | `0.45em` |
| `text.size` | `11pt` | `11pt` | `11.5pt` | `10.5pt` | `10.5pt` | `11pt` | `10.5pt` |
| `toc.depth` | `2` | — | — | — | `2` | `3` | `1` |
| `toc.enabled` | `True` | `False` | `False` | `False` | `True` | `True` | `True` |

## 取值格式

- 长度：`12pt`、`2.4cm`、`2em`、`0pt`
- 比例：`82%`
- 颜色：6 位十六进制，`#22645E` 或 `22645E`
- 布尔：`true` / `false`
- 字体栈：`["Libertinus Serif", "Noto Serif SC"]` 或逗号分隔字符串

## 示例

```yaml
kind: report
style:
  page:
    margin: 2.4cm
  heading:
    size-1: 18pt
    rule: true
  color:
    palette: indigo
```

```bash
python scripts/build_pdf.py build doc.md --set heading.size-1=18pt
python scripts/build_pdf.py build doc.md --doc doc.doc.yml
python scripts/build_pdf.py style doc.md --write doc.doc.yml
```
