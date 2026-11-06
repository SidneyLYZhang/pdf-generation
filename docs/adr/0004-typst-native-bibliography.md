# 引文交给 Typst 原生 bibliography 与 CSL 渲染，不用 pandoc --citeproc

pandoc 的 typst writer 会把 `[@key]` 原样写成 Typst 的 `@key`，而 Typst 自带 CSL 引擎和一批内置样式（实测 `gb-7714-2015-numeric` 直接可用）。让 pandoc 只做解析、由 Typst 在排版期读 `.bib` 并渲染，就能保留编号、反向链接、`@key[p. 5]` 定位与「作者-年」式引用；这些在 `--citeproc` 路线里都会退化成编译期定死的纯文本块，还会额外引入第二套 CSL 实现。

## Considered Options

- **`pandoc --citeproc`**：CSL 生态与 pandoc 完全一致，但输出是纯文本加一个 `<refs>` 块，丢链接、丢编号控制、丢目录条目，样式只能靠 show rule 硬拗。

## Consequences

- 引文样式是 Typst 的事：内置样式名与 `.csl` 文件路径都写在 `cite.style` 里，不存在两套 CSL 行为不一致的坑。
- 缺 bib 文件、缺 key 会在编译期硬失败（错误信息由构建脚本兜底翻译成人话），不会悄悄输出裸 key。
- 构建脚本要把书目路径转成 Typst 能解析的形式，和图片走同一套规则（同目录用相对路径，树外用根相对路径加 `--root`）。
