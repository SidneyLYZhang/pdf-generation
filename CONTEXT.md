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

**Scene**:
原则文档里的四种写作场景（论文、报告、小说、技术教材）。场景名是中文，Kind 名始终用英文标识符；两者是多对一映射而不是同义词，具体映射见 [references/typography.md](references/typography.md) 的「场景与 Kind」。
_Avoid_: 文档类型、类别、把场景直接叫 kind

**Citation**:
正文里指向一条参考条目的标注，写作 `[@key]`，显示形式（编号或「作者-年」）由 CSL 样式决定。
_Avoid_: 引用、reference

**Bibliography**:
文末的参考条目列表，数据来自 frontmatter 声明的 `.bib` / CSL-JSON / Hayagriva 文件。
_Avoid_: 文献表、参考文献列表、refs

**Cross-reference**:
正文里指向图、表、公式、节的标注，写作 `@fig:…` / `@tab:…` / `@eq:…` / `@sec:…`；数学里的 `\eqref{…}` 与 `\ref{…}` 是同一件事的另一种写法。编号由模板生成。
_Avoid_: 引用、ref、xref

**Sidenote**:
排在页边的注释；由显式标记或 `note.style` 触发，宽度来自加宽后的外侧页边。
_Avoid_: 旁注、marginnote、margin note

**Diagram**:
由 `mermaid` / `dot` 围栏在构建期预渲染成 SVG 的图，与图片共用题注与编号。
_Avoid_: 流程图、chart

**Chess diagram**:
由 `fen` / `pgn` 围栏经 staunton 排出的棋盘图，自带题注与编号；`notation` 围栏排出的是走法记谱，不是图。
_Avoid_: 棋谱图、board

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

**Principle check**:
构建前的门禁与构建后六项目检的合称。门禁分两档：结构性矛盾阻断构建（退出码 1），区间越界只警告，警告必须写进 Layout plan。
_Avoid_: 排版检查、lint

**Deviation**:
一条显式的偏离记录：规则标识、来源（机构规范或用户授权）与原因。它写在 doc.yml 的 `deviations:` 里，并随生成的 `.typ` 头部一起走，所以文件被搬走仍认自己那条记录。没有记录的偏离一律拒绝。
_Avoid_: 例外、豁免、override、绕过

**Layout plan**:
一次排版的交付说明，也就是「排版方案」：固定四行——方案、依据、自检、偏离。它是用户需求与原则的交集——用户要的效果落在原则之内，越界的部分换成最近邻或记成 Deviation。
_Avoid_: 设计稿、样式方案、版式说明

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
