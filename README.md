# PDF Generation

把 Markdown 排成一份像样的 PDF：**pandoc 解析，Typst 排版，不装 TeX Live**。

- **七种版式**：报告、文章、信函、笔记、书、教材、小说
- **可调排版**：五十多个旋钮，纸张、字体、行距、页眉、配色逐项可改
- **先问后做**：内置 Clarify 阶段，只问会改变成品的选择，并给推荐值
- **自包含产物**：生成的 `.typ` 内联整个模板，可直接 `typst compile` 复现

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

所有排版参数收敛在一个 Style spec 里，优先级：`--set` > frontmatter（元数据）> `<stem>.doc.yml` > Kind 默认 > 全局默认。

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

- 方言是 GFM + fenced div：任务列表、脚注、管道表格、`::: {.theorem}` 语义块都能用。
- 数学 `$x$` 内侧不能有空格；LaTeX 命令用 `\alpha`、`\frac` 这类合法写法。
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
│   ├── 20-frontmatter.typ   # 封面、文章标题块、目录、信函头尾
│   ├── 30-blocks.typ        # 定理/定义/例题等语义块
│   ├── 40-kinds.typ         # 小说章首、首字下沉
│   ├── 90-doc.typ           # 主装配
│   └── meta.typ             # pandoc 元数据模板
├── filters/semantic.lua     # ::: div → 语义块；章首首段标记
├── scripts/build_pdf.py     # detect / build / style / check / doctor
├── test/                    # 无第三方依赖的测试
├── references/              # kinds / style-knobs / authoring / troubleshooting
└── examples/                # 七种 Kind 各一份样张
```

## 测试

```bash
python -m unittest discover -s test -v
```

缺失 typst 或 pandoc 时，端到端用例自动跳过。

## 已知限制

- 没有参考文献/引文管理、边注、代码行号。
- Typst 0.15 在段距接近 0 时会把下一段抬高半行，构建脚本据此把最小段距定为 4.5pt；书/小说因此有一点点段间距。
- 不联网拉 Typst 包，模板全部内置。

## License

MIT，见 [LICENSE](LICENSE)。
