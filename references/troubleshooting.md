# 排错

先跑：

```bash
python scripts/build_pdf.py doctor
```

它会报 pandoc / typst 的版本、内置字体、中文字体，并用一段中文自检文档完整跑一遍构建。doctor 全绿再查具体问题。

## 构建阶段

### `找不到 pandoc` / `找不到 typst`

```text
错误：找不到 pandoc。安装：winget install JohnMacFarlane.Pandoc
```

按提示装；macOS 用 `brew install pandoc`，Linux 用包管理器。装完新开一个终端让 PATH 生效。

### `未知样式项 'page.margins'，是不是 page.margin ...?`

旋钮拼错了。报错里会列出最接近的三个合法项；完整清单见 [style-knobs.md](style-knobs.md)。

### `text.size 需要长度（如 2.5cm / 11pt），收到 'huge'`

值的格式不对。长度必须有单位（`pt` / `cm` / `mm` / `in` / `em`），比例用 `82%`，颜色用 6 位十六进制。

### `doc.yml` 解析失败

自带的 YAML 解析器只支持一个很小的子集：

- 只用空格缩进，不要 Tab
- 支持嵌套映射、`- ` 列表、引号字符串、布尔、数字、`|` 块文本
- 不支持锚点/引用（`&` / `*`）、多文档（`---`）、复杂 flow 集合

遇到解析不了的写法，改用 `--set`，或把值写成普通标量。

### Typst 报 `dictionary does not contain key "..."`

说明 Style spec 缺字段——通常是直接改坏了 `<stem>.typ`。删掉 `.typ` 重新 `build` 即可（`.typ` 每次构建都会重新生成）。

### `排版原则校验未通过：[indent-and-spacing] ...`

构建前的门禁拒绝了一个自相矛盾的 Style spec。现行两条规则：

- `indent-and-spacing`：首行缩进与可见段距同时在用，分段手段重复。把 `text.paragraph-spacing` 降到 4.5pt（Typst 的下限），让缩进独自分段。
- `spacing-below-leading`：没有首行缩进，段距却不大于行距间隙，段落之间看不出分隔。把 `text.paragraph-spacing` 提到行距间隙之上。

确实需要这样排（机构模板要求，或用户明确坚持），就写一条带原因的偏离：

```bash
python scripts/build_pdf.py build doc.md --deviation "indent-and-spacing=期刊模板要求段间空一行"
```

`--deviation` 只负责把记录写进 `<首个输入文件>.doc.yml`；真正放行的是文件里的记录，删掉它，同样的 spec 又会被拒。加 `--deviation-source standard` 把来源标记为机构规范（默认 `user`）。记录还会写进生成的 `.typ` 头部，所以 `.typ` 被改名或搬走后 `build x.typ` 仍认自己的豁免；头部没有记录、旁边也没有 doc.yml 时，它照样被拦。

没写原因的偏离一律拒绝，这是刻意的：静默绕过会让门禁变成装饰。

## 版式问题

### 段落叠在一起

Typst 0.15 在**段距接近 0** 时会把下一段抬高半行，导致行与行重叠。构建脚本会把小于 4.5pt 的段距抬到 4.5pt，所以正常情况下不会出现。

如果你手改了 `.typ`（`--keep-typ`）把 `spacing: 0pt` 写回去，就会复现。恢复默认即可。

### 中文变成方块 / 缺字

```text
warning: unknown font family: ...
```

说明字体栈里的中文字体没装。装 Noto Serif SC / Noto Sans SC（或思源宋体/黑体），或用 `--set text.font='["Libertinus Serif","你的字体"]'` 指定已安装的字体。

注意：字体栈是「按字形回退」的，西文用第一个能覆盖的字体、中文自动落到后面的中文字体。所以中文文档的栈一般写成 `("Libertinus Serif", "Noto Serif SC")`。

### 公式没渲染，原样显示 `$ x $`

两个原因，按顺序查：

1. `$` 内侧有空格：`$ x $` 不是数学，`$x$` 才是。
2. LaTeX 里有 pandoc 不认识的命令（如 `\/`）。构建日志会打印 `Could not convert TeX math ...`，按提示改命令。

### 表格太窄 / 字挤在一起

表格按内容宽度居中。列多时：

- 拆表；
- 或缩小字号：`--set text.size=10pt`；
- 或删掉不必要的列。

### 公式 / 图表没有编号

`book` 与 `article` 默认给公式编号，其余 Kind 默认关闭；图表默认编号一档。要改：

```bash
--set math.numbering="(1)"      # 公式显示 (1)；none 关闭
--set float.numbering="1"       # 图表显示 1
```

编号格式按单级计数器解释：`1.1` 只会显示 `1`。需要分级编号时，用编号格式本身表达不了，暂不支持。

### 某个旋钮设了没反应

1. 用 `python scripts/build_pdf.py style doc.md` 看解析后的最终值——优先级高的来源可能覆盖了它。
2. 检查名字是否拼错：拼错会直接报错，不会静默忽略。
3. 确认这个旋钮确实存在：[style-knobs.md](style-knobs.md) 是脚本从 schema 生成的，与代码同步。

### 目录是空的

- `toc.enabled` 是 `false`（letter / article 默认关闭）；
- 或者全文没有带层级的标题（`#` / `##`）。

### 信函里的换行没生效

`letter:` 字段里的换行必须写成 `\n`，而且要放在**双引号**字符串里：

```yaml
from: "示例公司\n示例市示例区示例路 88 号"
```

### 章名重复（「第一章 第一章 …」）

Kind 已经自动生成章号/「第 N 章」，源代码标题里不要再手写。删掉手写编号即可。

### 页码位置不对 / 封面也有页码

- 封面永远不显示页码。
- `furniture.page-number` 取 `footer-center` / `footer-right` / `footer-outside` / `none`。
- `footer-outside` 是奇偶镜像（书的切口页码），由模板用 `here().page()` 判断奇偶，不需要额外设置。

## 自检与产物

### 只看到命令行「成功」，但 PDF 有问题

默认只抽 1 页（文档中部）渲染 PNG。要全量看：

```bash
python scripts/build_pdf.py build doc.md --check all
# 或者对已有 .typ
python scripts/build_pdf.py check doc.typ --check all
```

PNG 落在 `<pdf 所在目录>/<stem>/`。

### 想直接改 Typst 源码

`<stem>.typ` 是自包含的（模板已内联），可以直接 `typst compile <stem>.typ`。两种例外会要求额外参数：图片在输出目录之外时要 `--root <项目根>`，用了棋谱时要 `--package-path <技能目录>/vendor/typst-packages`——生成的 `.typ` 头部有一行写好的完整命令。每次 `build` 会覆盖它；要迭代手改版本：

```bash
python scripts/build_pdf.py build doc.md          # 先生成 doc.typ
# 手改 doc.typ ...
python scripts/build_pdf.py build doc.md --keep-typ   # 复用已有 doc.typ，只重新编译
```

只想编译并检查一个 `.typ`（不重新生成）也可以直接：

```bash
python scripts/build_pdf.py build doc.typ
```

注意：手改后的 `.typ` 里如果写了 Markdown 风格的 `**粗体**`，Typst 会警告 `no text within stars`——那是 Markdown 语法，Typst 用 `*粗体*`。

### `failed to download package @preview/...`

本 skill 不依赖任何 Typst Universe 包。出现这个错误说明有人往模板里加了 `#import "@preview/..."`——删掉，或改用内置旋钮。

## 还是不行

把这三样贴出来：

1. `python scripts/build_pdf.py doctor` 的完整输出；
2. 出错命令的完整 stderr；
3. `<stem>.typ` 里 `#let style = (` 那一段（它记录了最终生效的所有旋钮）。
