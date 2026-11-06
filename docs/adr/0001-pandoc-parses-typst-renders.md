# pandoc 解析 Markdown，Typst 负责排版

原技能用 Pandoc + XeLaTeX，依赖数 GB 的 TeX 发行版，且版式能力锁在 Eisvogel/LaTeX 里，无法干净地暴露"排版旋钮"。改为：pandoc 只做 `-f gfm -t typst` 的语法解析，版式全部由 skill 自带的 Typst 模板承担，Typst 直接出 PDF。仍然保留 pandoc，是因为 LaTeX 数学转 Typst 数学、表格、脚注与嵌套列表这些解析工作，自研脚本的稳定性远不如它；`-f gfm` 还顺带修掉了旧 `fix_markdown.py` 要处理的"冒号后列表被吞成一段"问题。

## Considered Options

- **纯 Python 自研转换器**：零 pandoc 依赖，但数学转换与 Markdown 边界情况要重造轮子，维护成本高。
- **保留 Pandoc + LaTeX**：依赖重，且版式只能靠 LaTeX 模板参数间接调整。

## Consequences

- skill 运行时必须能调用 pandoc，需要在生成前检测并给出安装提示。
- Markdown 方言固定为 GFM（外加按需开启的 pandoc 扩展），文档里需要写明。
