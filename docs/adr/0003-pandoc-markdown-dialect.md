# 解析方言改用 pandoc markdown，`@` 按前缀分派到交叉引用与引文

GFM 不支持 `citations` 扩展，`[@key]` 只是一段普通文字；它同时关掉了 `attributes` 与 `implicit_figures`，于是「图片宽度 70%」「图题注位置」这些既写进了文档、也做成了旋钮的能力从未生效。留在 GFM 就得自己用正则重写整套引用语法。决定：解析格式改为 pandoc `markdown`，并把扩展串钉成一条常量，用 `lists_without_preceding_blankline` 换回「冒号后列表」的解析手感，关掉 `smart` 与 `raw_tex` 以免标点和 LaTeX 命令悄悄改变含义。同时约定 `@` 的两种含义：后跟 `fig:` `tab:` `eq:` `sec:` 前缀的是交叉引用，其余是引文——这是 pandoc-crossref 已经打成事实标准的约定。

## Considered Options

- **留在 GFM，用 Lua filter 手搓引文语法**：方言不动，但引用集群、定位、前后缀都要自己实现，图片属性依旧不可用。
- **双方言（有 `.bib` 走 markdown，否则 gfm）**：两套解析、两套测试、两套文档，作者得先知道自己处在哪一档。

## Consequences

- 切换时逐条比对七份样张的输出；现有内容预期零差异（已验证 `examples/report.md` 在两种方言下输出完全一致）。
- `@doe2020` 这类裸 `@` 从此有语法含义：邮箱、社交账号、以及 Typst 式 `@fig:1` 都必须按新约定书写，文档要明说。
- 方言串是常量而非散落的 CLI 参数，升级 pandoc 时只改一处。
