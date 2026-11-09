# 引文与书目

书目由 Typst 原生 bibliography + CSL 渲染（ADR-0004），pandoc 只负责把 `[@key]` 解析成引文。

## 声明书目

```yaml
---
title: 报告
bibliography: references.bib
---
```

- 支持 `.bib`（BibTeX）、`.json`（CSL-JSON）、`.yml`（Hayagriva），路径相对**首个** Markdown 文件。
- 多文件书稿：书目只在第一个文件的 frontmatter 里写，列表落在全文末尾。
- 声明之后正文的 `[@key]` 就是引文；不声明 `bibliography` 时，引用会让构建失败并指出那个 key（Typst 找不到引文标签），不会悄悄排出裸文本。

## 写法

```markdown
已有研究指出[@doe2020]，另一项工作给出不同结论[@smith2021]。
带页码定位：[@doe2020, p. 33]。
一次引多条：[@doe2020; @smith2021]。
```

- 缺文件、缺 key 都会让构建失败并指出名字，不会悄悄排出裸 key。
- 参考文献标题默认按语言取「参考文献 / References」，进目录；`cite.title` 可改。

## 样式

| 场景 | 默认样式 |
|------|----------|
| 中文文档 | `gb-7714-2015-numeric` |
| 英文文档 | `ieee` |
| `article`（任意语言） | `apa` |

换样式：`--set cite.style=apa`、`cite.style: nlm-citation-sequence`，或指向一个 `.csl` 文件：

```bash
python scripts/build_pdf.py build doc.md --set cite.style=./styles/custom.csl
```

`.csl` 路径相对 Markdown 文件解析，绝对路径会被改写成 Typst 能吃的形式。可用样式名由 Typst 自带（`apa` / `ieee` / `mla` / `chicago-author-date` / `nlm-citation-sequence` / `gb-7714-2015-numeric` 等）；`doctor` 会试编三个默认样式。

## 与交叉引用的分工

`@` 后面跟**保留前缀**的是交叉引用，其余才是引文：

| 前缀 | 指向 |
|------|------|
| `fig:` | 图 |
| `tab:` | 表 |
| `eq:` | 公式（`\eqref{}` / `\ref{}` 也行） |
| `sec:` | 节 |

所以书目 key 不要用这四个前缀。规则细节见 [authoring.md](authoring.md)。

## 坑

- `gb-7714-2015-numeric` 不显示页码定位（CSL 实现所限），需要页码就用 `ieee` / `apa`，或把页码写进正文。
- 引文样式只认**内置名或 `.csl` 文件**；写错名字会得到 Typst 的样式解析错误，构建退出码非零。
- 参考文献列表本身不参与图/表/公式编号。
