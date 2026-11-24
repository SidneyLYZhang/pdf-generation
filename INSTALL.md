# 安装

这个技能只有三样运行时依赖（Typst、pandoc、Python），没有安装包、没有编译、不联网。下面分两部分：**给用户**（人来做）和**给 Agent**（由 agent 执行或自查）。

---

## 第一部分：给用户

### 1. 装依赖

| 依赖 | 版本 | Windows | macOS | Linux |
|------|------|---------|-------|-------|
| Typst | ≥ 0.15 | `winget install Typst.Typst` 或 `scoop install typst` | `brew install typst` | `apt install typst` / `cargo install typst-cli` |
| pandoc | ≥ 3.1 | `winget install JohnMacFarlane.Pandoc` | `brew install pandoc` | `apt install pandoc` |
| Python | ≥ 3.9 | 系统已带，或用 `winget install Python.Python.3.12` | 系统已带 | 系统已带 |

装完**重开一个终端**，确认三者都在 PATH 里：

```bash
typst --version
pandoc --version
python --version
```

### 2. 装中文字体（排中文才需要）

模板默认西文用 Typst 内置字体，中文按字体栈回退到：

1. `Noto Serif SC`（正文）/ `Noto Sans SC`（标题）
2. `Source Han Serif SC` / `Source Han Sans SC`（思源宋体/黑体）
3. 系统宋体 / 黑体

装前两项里的任意一组即可。免费下载：

- Noto Serif SC：<https://fonts.google.com/noto/specimen/Noto+Serif+SC>
- Noto Sans SC：<https://fonts.google.com/noto/specimen/Noto+Sans+SC>
- 思源宋体 / 思源黑体（Adobe 版）：<https://github.com/adobe-fonts/source-han-serif>

Windows 用户也可以直接用系统自带的「宋体」「黑体」，观感差一档但不会缺字。装完用 `typst fonts` 确认字体名出现在列表里。

### 3. 放置技能

**DSH（首选）**

```text
Windows:  C:\Users\<你>\.dsh\skills\pdf-generation\
macOS/Linux:  ~/.dsh/skills/pdf-generation/
```

把整个目录放进去（`SKILL.md` 必须在目录根部，目录名与 `SKILL.md` 里的 `name` 一致）。重启会话，或在技能列表里重新加载，`pdf-generation` 即会出现。

**Claude Code**

```text
~/.claude/skills/pdf-generation/
```

同上，放整个目录。

**从 GitHub 克隆（二选一）**

```bash
git clone https://github.com/SidneyLYZhang/pdf-generation.git ~/.dsh/skills/pdf-generation
# 或
git clone https://github.com/SidneyLYZhang/pdf-generation.git ~/.claude/skills/pdf-generation
```

**其他 Agent**

技能不依赖任何宿主专有工具。把目录放到对方的技能目录，或在系统提示里指向 `SKILL.md` 即可；没有「技能目录」概念的宿主，直接把 `SKILL.md` 作为该任务的说明喂给它。

### 4. 30 秒验证

```bash
cd ~/.dsh/skills/pdf-generation
python scripts/build_pdf.py doctor
python scripts/build_pdf.py build examples/report.md
```

`doctor` 应逐行打印 `ok`，最后一行是 `模板自检 N 页`。第二条命令结束后，`examples/report.pdf` 应该存在，并打印出抽页 PNG 的路径——打开它看一眼，中文不是方块就成功了。构建前会过一遍排版原则门禁，默认值全部合规，正常不会拦你；被拦时见 [references/troubleshooting.md](references/troubleshooting.md) 的「排版原则校验未通过」。

### 5. 更新与卸载

```bash
cd ~/.dsh/skills/pdf-generation && git pull     # 更新
rm -rf ~/.dsh/skills/pdf-generation             # 卸载
```

技能不写系统目录、不改 PATH、不注册服务；删目录即卸载干净。

### 安装阶段的常见问题

| 现象 | 原因与处理 |
|------|------------|
| `找不到 typst` / `找不到 pandoc` | PATH 未生效：重开终端；仍不行则用绝对路径确认安装位置 |
| `python` 不存在，只有 `py` | Windows 用 `py scripts/build_pdf.py ...`，或装 Python 时勾选 “Add to PATH” |
| 中文全是方块 | 字体没装或少装：`typst fonts` 里应出现 `Noto Serif SC` |
| 想用自己的字体 | `--set text.font='["Your Serif","Noto Serif SC"]'`，或在 `doc.yml` 里写字体栈 |
| 公司代理 / 证书 | 与本技能无关：Typst、pandoc、模板都不联网 |
| `排版原则校验未通过` | 不是安装问题：旋钮改出了自相矛盾的组合。按报错改旋钮，或写一条带原因的偏离，见 troubleshooting |
| macOS 提示 Typst 无法验证 | 系统设置 → 隐私与安全性 → 仍要打开 |

### 附：棋谱包（已内联，无需安装）

棋谱用的 Typst 包 `staunton` 2.0.0 已经内联在仓库的 `vendor/typst-packages/` 下，构建时通过 `--package-path` 解析，**不需要联网、也不需要往 Typst 全局缓存里装东西**。`doctor` 会编译一个空棋盘验证它能 import。

升级它（只在想换版本时做）：

1. 用新版本的发布包整体替换 `vendor/typst-packages/preview/staunton/<版本>/`；
2. 改 `scripts/build_pdf.py` 里钉住的版本号（`STAUNTON_VERSION`）；
3. 重跑 `python scripts/build_pdf.py doctor` 确认内联包可 import，再抽一页看看棋盘。

注意许可：棋子 SVG 是 GPL-2.0-or-later，该目录单独挂 `LICENSE` 与 `NOTICE.md`，仓库其余部分仍是 MIT。

构建时会自动带上 `--package-path`；手工 `typst compile` 一份含棋谱的 `.typ` 时也要加，生成的 `.typ` 头部注释里写了完整命令。

### 附：图表渲染器（可选）

`dot` / `mermaid` 围栏要出图，才需要对应的渲染器：

| 语言 | 工具 | 安装 |
|------|------|------|
| `dot` | Graphviz | `winget install Graphviz.Graphviz` / `brew install graphviz` / `apt install graphviz` |
| `mermaid` | mermaid-cli | `npm i -g @mermaid-js/mermaid-cli` |

没装也能构建：给一条警告，对应的图按源码代码块排出。`doctor` 会分别报告两者的可用性。装了 `mmdc` 的机器上，构建会在源文件旁的 `.pdfgen/diagrams/` 缓存 SVG，同样的图不会重复渲染。

---

## 第二部分：给 Agent

你正在把这个技能装进一个宿主。按顺序做，每步都有判定条件。

### 1. 找到宿主的技能目录

| 宿主 | 目录 | 判定 |
|------|------|------|
| DSH | `~/.dsh/skills/<name>/` | 目录存在后重启会话，技能列表出现该 name |
| Claude Code | `~/.claude/skills/<name>/` | 同上，技能可被 `/name` 调用 |
| 其他 | 问用户技能目录，或确认对方是否读取 `SKILL.md` | 用户确认加载方式 |

目录名与 `SKILL.md` 的 `name:` 保持一致（默认 `pdf-generation`）。**完成后**：`SKILL.md` 位于该目录根部。

### 2. 检查依赖

```bash
python scripts/build_pdf.py doctor
```

**判定**：每一行都是 `[ok]`，且最后一行形如 `[ok] 模板自检 N 页`。

出现 `[fail]` 时按「第一部分 · 1」的表格安装，重开终端后重跑。没有安装权限就把缺失项和对应命令告诉用户。

### 3. 验证一次真实构建

```bash
python scripts/build_pdf.py build examples/report.md
```

**判定**：退出码为 0，打印 `PDF ... (N 页)`，`examples/report.pdf` 存在。

### 4. 确认视觉自检能力

构建会打印一张抽页 PNG 的路径。你能读图就打开它，确认中文不是方块、封面没有错位；读不了图就用 `--check none` 构建，并在交付时明确告诉用户「未做视觉自检」。

**判定**：你对「能否读图」有明确结论，并已据此选择 `--check sample` 或 `--check none`。

### 目录契约

```
<skill>/
├── SKILL.md          ← 必需，必须在根部，name 与目录名一致
├── CONTEXT.md        ← 术语表；SKILL.md 链着它，漏搬会出现断链
├── scripts/build_pdf.py
├── scripts/gen_style_docs.py   ← 只在重新生成文档表格时用，可选
├── template/*.typ    ← 构建时按文件名顺序内联
├── filters/features.lua
├── filters/refs.lua
├── filters/semantic.lua
├── filters/diagrams.lua
├── filters/chess.lua
├── vendor/typst-packages/   ← 棋谱用的 staunton，漏搬会让含棋谱的文档构建失败
├── references/*.md
└── examples/*.md
```

- 脚本用「自身位置」定位技能根（`scripts/../`），**整个目录一起搬**，不要只复制 `SKILL.md`。
- 不要改 `template/` 内的相对路径假设；构建时模板会被拼进同一个 `.typ`。
- 运行时不需要网络：模板自带、不拉 Typst 包。
- `docs/` 与 `test/` 只服务仓库维护（原则原文、决策记录、测试），运行时代码不读它们，装的时候可以不带。

### 宿主差异

| 能力 | DSH | Claude Code | 通用 |
|------|-----|-------------|------|
| 结构化提问 | `ask_user_question` | `AskUserQuestion` | 编号文本 |
| 技能发现 | `~/.dsh/skills` | `~/.claude/skills` | 手动指向 `SKILL.md` |
| 受限 shell | 可能需要用户批准写文件 | 同左 | 按宿主策略 |

### 自测（可选）

仓库带一套无第三方依赖的测试：

```bash
python -m unittest discover -s test -v
```

它覆盖 YAML 子集解析、样式优先级、CLI 参数校验、抽页规则、排版原则门禁与偏离通道、生成文档与代码的一致性，以及七种 Kind 的端到端构建（缺 typst/pandoc 时自动跳过）。

