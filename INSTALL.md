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

`doctor` 应逐行打印 `ok`，最后一行是 `模板自检 N 页`。第二条命令结束后，`examples/report.pdf` 应该存在，并打印出抽页 PNG 的路径——打开它看一眼，中文不是方块就成功了。

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
| macOS 提示 Typst 无法验证 | 系统设置 → 隐私与安全性 → 仍要打开 |

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
├── scripts/build_pdf.py
├── template/*.typ    ← 构建时按文件名顺序内联
├── filters/semantic.lua
├── references/*.md
└── examples/*.md
```

- 脚本用「自身位置」定位技能根（`scripts/../`），**整个目录一起搬**，不要只复制 `SKILL.md`。
- 不要改 `template/` 内的相对路径假设；构建时模板会被拼进同一个 `.typ`。
- 运行时不需要网络：模板自带、不拉 Typst 包。

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

它覆盖 YAML 子集解析、样式优先级、CLI 参数校验、抽页规则，以及七种 Kind 的端到端构建（缺 typst/pandoc 时自动跳过）。
