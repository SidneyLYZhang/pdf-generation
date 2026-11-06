# PDF Generation

把一个 Markdown 文件变成 PDF：Typst 排版，pandoc 只做语法解析。这份术语表约束 skill 的指令、脚本参数与文档用词，避免同一个概念出现三种叫法。

## Language

**Kind**:
文档的版式家族，决定封面、目录、编号、分页与环境等整套行为；取值为 report、article、letter、note、book、textbook、novel。
_Avoid_: 文档类型、模板类型、template、doc type

**Report**:
默认 Kind。A4、封面可选、带目录与编号标题、图表与页眉页脚齐备的通用报告。
_Avoid_: 白皮书、paper（指 article 时也避免）

**Article**:
单篇成文：标题块、摘要、正文；不分章、无封面。长文用"章起新页"表达，不另立 Kind。
_Avoid_: 长文、长文 kind、essay

**Letter**:
由发件人、收件人、日期、称呼、正文、落款构成的一页式信函；无目录、无标题编号。
_Avoid_: 邮件、mail、信

**Note**:
紧凑排版的笔记：无封面、少留白，可按需启用定理与代码块。
_Avoid_: 随堂笔记、memo

**Book**:
带封面、目录、章起新页、页眉与页码的长文档。
_Avoid_: 书、书籍

**Textbook**:
在 Book 之上加入定理、定义、例题、习题等语义块与边注的教材版式。
_Avoid_: 教材、teaching material

**Novel**:
带封面、章首装饰、首字下沉与段首缩进，标题不编号的小说版式。
_Avoid_: 小说、fiction

**Style spec**:
用户可调的排版参数集合，是某一文档排版的唯一事实源。
_Avoid_: 样式表、样式文件、style.typ、配置

**Knob**:
Style spec 中的单个可调参数，例如页边距、正文字号、标题配色。
_Avoid_: 参数、选项、设置项

**Palette**:
一套配色取值（强调色、正文色、浅底色、细线色），与版式无关，可被任意 Kind 复用。
_Avoid_: 主题、theme、配色方案

**Preset**:
某个 Kind 的默认 Knob 取值组合。
_Avoid_: 模板、template、默认样式

**Clarify phase**:
生成前汇总不确定信息并向用户提问的阶段，只问会改变成品的项。
_Avoid_: 需求确认、访谈、问卷

**Declarative auto-confirm**:
不阻塞的自动确认：先声明选定的 Kind 与关键 Knob，再直接开始生成，用户可随后推翻。
_Avoid_: 自动确认、默认确认

**Render**:
用 Typst 把样式化的中间文件编译成 PDF。
_Avoid_: 转换、导出、build

**Build**:
从 Markdown 到 PDF 的完整流程：解析 → 套模板 → Render。
_Avoid_: 生成、generate、出图
