#!/usr/bin/env python3
"""pdf-generation: Markdown -> PDF, parsed by pandoc, laid out by Typst.

The bundled template in ``template/`` owns every layout decision.  pandoc is
used only as a Markdown parser (the dialect pinned in ``FROM_FORMAT``); Typst
renders the PDF.

Subcommands
-----------
detect   Inspect the source files and print the facts a Clarify phase needs.
build    Resolve the style spec, parse, render, self-check.
style    Print (or write) the resolved Style spec.
check    Re-check an existing ``.typ`` file.
doctor   Verify pandoc/typst/font availability.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_ROOT / "template"
META_TEMPLATE = TEMPLATE_DIR / "meta.typ"
LUA_FILTER = SKILL_ROOT / "filters" / "semantic.lua"
# Runs before semantic.lua: it rewrites notes and code blocks, which must happen
# before fenced Divs are flattened into raw Typst.
FEATURE_FILTER = SKILL_ROOT / "filters" / "features.lua"
# No-op unless the build passed a `pdfgen-diagrams` metadata file.
DIAGRAM_FILTER = SKILL_ROOT / "filters" / "diagrams.lua"
# Vendored Typst Universe packages (ADR-0005).  Typst resolves `@preview/...`
# imports here when `--package-path` points at it, so no network is needed.
VENDOR_PACKAGES = SKILL_ROOT / "vendor" / "typst-packages"
# Pinned by ADR-0005; change here and in the vendored directory together.
STAUNTON_VERSION = "2.0.0"

KINDS = ("report", "article", "letter", "note", "book", "textbook", "novel")

# The Markdown dialect is a pinned constant, not pandoc's default, so that a
# pandoc upgrade cannot silently change how documents parse (ADR-0003).
#   +lists_without_preceding_blankline  keep GFM's "list right after a colon line"
#   +fenced_divs                        ::: semantic blocks and page breaks
#   +bracketed_spans                    inline margin notes [text]{.marginnote}
#   +fenced_code_attributes             fence options: {line-numbers}, chess options
#   +citations                          [@key] citations and @fig: cross-references
#   +implicit_figures                   a lone image becomes a captioned figure
#   -smart                              no curly quotes / dash substitution
#   -raw_tex -latex_macros              unsupported LaTeX stays visible text
FROM_FORMAT = (
    "markdown+lists_without_preceding_blankline+fenced_divs+bracketed_spans"
    "+fenced_code_attributes+citations+implicit_figures-smart-raw_tex-latex_macros"
)

# --------------------------------------------------------------------------- #
# Style spec
# --------------------------------------------------------------------------- #
# Each knob: dotted key -> (type, default).  "auto" is resolved at finalise
# time (palette colours, fonts, caption positions).  Unknown keys are an error
# so a typo never silently does nothing.
KNOBS: dict[str, tuple[str, object]] = {
    # page -------------------------------------------------------------------
    "page.paper": ("paper", "a4"),
    "page.margin": ("length", "2.5cm"),
    "page.gutter": ("length", "0cm"),
    # text -------------------------------------------------------------------
    "text.font": ("fontlist", "auto"),
    "text.heading-font": ("fontlist", "auto"),
    "text.size": ("length", "11pt"),
    "text.leading": ("length", "0.65em"),
    "text.paragraph-spacing": ("length", "1em"),
    "text.first-line-indent": ("length", "0em"),
    "text.justify": ("bool", True),
    "text.hyphenate": ("bool", True),
    "text.lang": ("str", "auto"),
    # heading ----------------------------------------------------------------
    "heading.size-1": ("length", "20pt"),
    "heading.size-2": ("length", "14pt"),
    "heading.size-3": ("length", "11.5pt"),
    "heading.color": ("color", "auto"),
    "heading.numbering": ("numbering", "1.1"),
    "heading.page-break-before": ("bool", False),
    "heading.space-before": ("length", "1.6em"),
    "heading.space-after": ("length", "0.7em"),
    "heading.rule": ("bool", False),
    # colour -----------------------------------------------------------------
    "color.palette": ("palette", "teal"),
    "color.accent": ("color", "auto"),
    "color.ink": ("color", "auto"),
    "color.muted": ("color", "auto"),
    "color.rule": ("color", "auto"),
    "color.link": ("color", "auto"),
    "color.code-bg": ("color", "auto"),
    "color.tint": ("color", "auto"),
    # page furniture ---------------------------------------------------------
    "furniture.header": ("header", "auto"),
    "furniture.header-rule": ("bool", True),
    "furniture.page-number": ("pagenumber", "auto"),
    "furniture.page-number-format": ("str", "1"),
    # cover ------------------------------------------------------------------
    "cover.enabled": ("bool", "auto"),
    "cover.style": ("coverstyle", "auto"),
    "cover.tagline": ("str", ""),
    "cover.logo": ("str", ""),
    # table of contents ------------------------------------------------------
    "toc.enabled": ("bool", "auto"),
    "toc.depth": ("int", "auto"),
    "toc.title": ("str", "auto"),
    # floats -----------------------------------------------------------------
    "float.figure-caption": ("captionpos", "bottom"),
    "float.table-caption": ("captionpos", "top"),
    "float.numbering": ("numbering", "1"),
    "float.figure-width": ("ratio", "82%"),
    # code -------------------------------------------------------------------
    "code.theme": ("codetheme", "default"),
    "code.size": ("length", "9pt"),
    "code.header": ("bool", True),
    "code.line-numbers": ("bool", False),
    # math -------------------------------------------------------------------
    "math.numbering": ("numbering", "none"),
    # margin notes -----------------------------------------------------------
    "note.style": ("notestyle", "footnote"),
    "note.width": ("length", "4.2cm"),
    "note.gap": ("length", "12pt"),
    "note.size": ("length", "8pt"),
    # citations --------------------------------------------------------------
    "cite.enabled": ("bool", "auto"),
    "cite.style": ("str", "auto"),
    "cite.title": ("str", "auto"),
    # semantic blocks --------------------------------------------------------
    "semantic.numbering": ("numbering", "1"),
    # kind specific ----------------------------------------------------------
    "novel.dropcap": ("bool", "auto"),
    "novel.chapter-prefix": ("bool", "auto"),
}

PALETTES: dict[str, dict[str, str]] = {
    "teal": {
        "accent": "#22645E",
        "ink": "#1F2328",
        "muted": "#5B6468",
        "rule": "#D7DCDB",
        "link": "#22645E",
        "code-bg": "#F4F6F5",
        "tint": "#EEF4F2",
    },
    "indigo": {
        "accent": "#45578B",
        "ink": "#1C2233",
        "muted": "#5A6072",
        "rule": "#D9DCE6",
        "link": "#45578B",
        "code-bg": "#F4F5FA",
        "tint": "#EDEFF7",
    },
    "sepia": {
        "accent": "#855C35",
        "ink": "#2A2118",
        "muted": "#6B5B4B",
        "rule": "#E2D9CC",
        "link": "#855C35",
        "code-bg": "#F8F4EE",
        "tint": "#F5EEE5",
    },
    "mono": {
        "accent": "#333333",
        "ink": "#000000",
        "muted": "#555555",
        "rule": "#D8D8D8",
        "link": "#333333",
        "code-bg": "#F7F7F7",
        "tint": "#F2F2F2",
    },
}

# Partial overrides per Kind.  Everything not listed falls back to KNOBS.
PRESETS: dict[str, dict[str, object]] = {
    "report": {
        "cover.enabled": True,
        "cover.style": "band",
        "toc.enabled": True,
        "toc.depth": 2,
        "heading.numbering": "1.1",
        "heading.page-break-before": False,
        "heading.size-1": "22pt",
        "heading.rule": False,
        "furniture.header": "title",
        "furniture.page-number": "footer-center",
        "text.paragraph-spacing": "1em",
        "text.first-line-indent": "0em",
        "text.size": "11pt",
        "semantic.numbering": "none",
    },
    "article": {
        "cover.enabled": False,
        "toc.enabled": False,
        "heading.numbering": "1.1",
        "heading.page-break-before": False,
        "heading.size-1": "19pt",
        "furniture.header": "none",
        "furniture.page-number": "footer-center",
        "text.paragraph-spacing": "0.9em",
        "text.first-line-indent": "0em",
        "text.size": "11pt",
    },
    "letter": {
        "cover.enabled": False,
        "toc.enabled": False,
        "heading.numbering": "none",
        "heading.page-break-before": False,
        "heading.size-1": "14pt",
        "heading.rule": False,
        "furniture.header": "none",
        "furniture.page-number": "none",
        "text.paragraph-spacing": "1.2em",
        "text.first-line-indent": "0em",
        "text.size": "11.5pt",
        "page.margin": "3cm",
    },
    "note": {
        "cover.enabled": False,
        "toc.enabled": False,
        "heading.numbering": "none",
        "heading.page-break-before": False,
        "heading.size-1": "17pt",
        "furniture.header": "none",
        "furniture.page-number": "footer-right",
        "text.paragraph-spacing": "0.5em",
        "text.first-line-indent": "0em",
        "text.size": "10.5pt",
        "text.leading": "0.6em",
    },
    "book": {
        "page.paper": "6x9",
        "page.margin": "2cm",
        "cover.enabled": True,
        "cover.style": "band",
        "toc.enabled": True,
        "toc.depth": 2,
        "heading.numbering": "1.1",
        "heading.page-break-before": True,
        "heading.size-1": "22pt",
        "heading.size-2": "15pt",
        "heading.size-3": "12pt",
        "heading.rule": True,
        "furniture.header": "book",
        "furniture.page-number": "footer-outside",
        "text.paragraph-spacing": "0.45em",
        "text.first-line-indent": "2em",
        "text.size": "10.5pt",
        "novel.dropcap": False,
        "novel.chapter-prefix": False,
    },
    "textbook": {
        "page.paper": "a4",
        "page.margin": "2.4cm",
        "cover.enabled": True,
        "cover.style": "band",
        "toc.enabled": True,
        "toc.depth": 3,
        "heading.numbering": "1.1.1",
        "heading.page-break-before": True,
        "heading.size-1": "22pt",
        "heading.size-2": "15pt",
        "heading.size-3": "12pt",
        "heading.rule": True,
        "furniture.header": "chapter",
        "furniture.page-number": "footer-outside",
        "text.paragraph-spacing": "0.35em",
        "text.first-line-indent": "2em",
        "text.size": "11pt",
        "semantic.numbering": "1",
        "note.style": "margin",
        "novel.dropcap": False,
        "novel.chapter-prefix": False,
    },
    "novel": {
        "page.paper": "a5",
        "page.margin": "2.2cm",
        "cover.enabled": True,
        "cover.style": "minimal",
        "toc.enabled": True,
        "toc.depth": 1,
        "heading.numbering": "none",
        "heading.page-break-before": True,
        "heading.size-1": "20pt",
        "heading.rule": False,
        "furniture.header": "none",
        "furniture.page-number": "footer-center",
        "text.paragraph-spacing": "0.45em",
        "text.first-line-indent": "2em",
        "text.size": "10.5pt",
        "novel.dropcap": True,
        "novel.chapter-prefix": True,
    },
}

PAPERS = {"a4", "a5", "6x9", "letter"}
COVER_STYLES = {"band", "full", "minimal"}
PAGE_NUMBERS = {"none", "footer-center", "footer-right", "footer-outside"}
HEADERS = {"none", "title", "book", "chapter"}
CAPTION_POS = {"top", "bottom"}
CODE_THEMES = {"default", "none"}

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LATIN_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")

# Margin notes, both written as `{.sidenote}`: inline on a span, block on a div.
INLINE_NOTE_RE = re.compile(r"\[([^\]]*)\]\{[^}]*\.sidenote[^}]*\}")
BLOCK_NOTE_RE = re.compile(r":::+\s*\{[^}]*\.sidenote[^}]*\}[^\n]*\n(.*?):::", re.S)
FOOTNOTE_DEF_RE = re.compile(r"^\[\^[^\]]+\]:[ \t]*(.+)$", re.M)
PAGEBREAK_RE = re.compile(r":::\s*pagebreak\s*:::")
LONG_NOTE_CHARS = 200
# Rough stand-in for vertical distance: about two notes' worth of body text.
NOTE_GAP_CHARS = 80


def prose_only(text: str) -> str:
    """Drop fenced code blocks: a syntax example must not look like the syntax."""
    lines = text.splitlines()
    dropped: set[int] = set()
    for start, end, _, _, _ in iter_fences(text):
        dropped.update(range(start, end + 1))
    return "\n".join(line for number, line in enumerate(lines, 1) if number not in dropped)


def inspect_sidenotes(text: str, include_footnotes: bool = False) -> tuple[bool, list[int], int]:
    """What a build must know about margin notes: present, long ones, tight pairs.

    A pair is "tight" when the distance between the end of one note and the start
    of the next is small: the note's own text moves to the margin, so it must not
    count as spacing.  Pairs split by an explicit page break can never collide.
    """
    prose = prose_only(text)
    inline = list(INLINE_NOTE_RE.finditer(prose))
    blocks = list(BLOCK_NOTE_RE.finditer(prose))
    spans = [(match.start(), match.end()) for match in inline + blocks]
    lengths = [len(match.group(1)) for match in inline]
    lengths += [len(match.group(1).strip()) for match in blocks]

    if include_footnotes:
        footnotes = list(FOOTNOTE_DEF_RE.finditer(prose))
        spans += [(match.start(), match.end()) for match in footnotes]
        lengths += [len(match.group(1)) for match in footnotes]

    spans.sort()
    breaks = [match.start() for match in PAGEBREAK_RE.finditer(prose)]
    crowded = sum(
        1
        for (_, prev_end), (next_start, _) in zip(spans, spans[1:])
        if next_start - prev_end < NOTE_GAP_CHARS
        and not any(prev_end < b < next_start for b in breaks)
    )
    overlong = [length for length in lengths if length > LONG_NOTE_CHARS]
    return bool(inline or blocks), overlong, crowded

# Diagrams: a `mermaid` or `dot` fence is rendered to SVG at build time and
# turned into a normal figure, so the float knobs and @fig: references apply.
# The rendered paths reach pandoc as a metadata file; filters/diagrams.lua looks
# blocks up by their position, so two identical diagrams stay distinct.
DIAGRAM_RENDERERS = {
    "mermaid": ("mmdc", "npm i -g @mermaid-js/mermaid-cli"),
    "dot": ("dot", "winget install Graphviz.Graphviz"),
}
DIAGRAM_ATTRS = ("caption", "width", "id")
FENCE_OPEN_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})[ \t]*(?P<info>.*)$")
ATTR_PAIR_RE = re.compile(r'([A-Za-z][\w-]*)=(?:"((?:[^"\\]|\\.)*)"|(\S+))')
LENGTH_ATTR_RE = re.compile(r"^\d+(\.\d+)?(pt|cm|mm|in|em|%)$")
LABEL_RE = re.compile(r"^[A-Za-z0-9_:.\-]+$")


def iter_fences(text: str):
    """Yield (start_line, end_line, indent, info, body_lines) for each fenced block."""
    fence, info, body, start, indent = None, "", [], 0, 0
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if fence is None:
            match = FENCE_OPEN_RE.match(stripped)
            if match:
                indent = len(line) - len(line.lstrip())
                # Four or more spaces means an indented code block, not a
                # fence: pandoc would render the fence text literally.
                if indent <= 3:
                    fence, info, body, start = match.group("fence"), match.group("info"), [], number
            continue
        if stripped.startswith(fence) and set(stripped) == {fence[0]}:
            yield start, number, indent, info, body
            fence = None
            continue
        # Pandoc strips the fence's own indentation from the code, so the
        # lookup key has to be built from the same text.
        body.append(line[indent:] if line[:indent].strip() == "" else line.lstrip())


def parse_fence_info(info: str) -> tuple[str, dict[str, str]]:
    """`dot {caption="接口" width=60%}` -> ("dot", {...})."""
    info = info.strip()
    if not info:
        return "", {}
    if "{" in info:
        lang, _, rest = info.partition("{")
        attrs_text = rest.rsplit("}", 1)[0]
    else:
        lang, attrs_text = info, ""
    attrs: dict[str, str] = {}
    for match in ATTR_PAIR_RE.finditer(attrs_text):
        quoted = match.group(2)
        if quoted is not None:
            quoted = quoted.replace('\\"', '"').replace("\\\\", "\\")
        attrs[match.group(1)] = quoted if quoted is not None else match.group(3)
    for match in re.finditer(r"#([A-Za-z0-9_:.\-]+)", attrs_text):
        attrs["id"] = match.group(1)
    return lang.strip().lower(), attrs


def find_diagram_blocks(text: str) -> list[dict]:
    """Diagram fences in `text`, with the line their fence starts on."""
    blocks: list[dict] = []
    for start, _, _, info, body in iter_fences(text):
        lang, attrs = parse_fence_info(info)
        if lang not in DIAGRAM_RENDERERS:
            continue
        unknown = sorted(set(attrs) - set(DIAGRAM_ATTRS))
        if unknown:
            raise SpecError(
                f"第 {start} 行的 {lang} 图有不认识的选项：{', '.join(unknown)}；"
                f"可用：{', '.join(DIAGRAM_ATTRS)}"
            )
        blocks.append({"lang": lang, "attrs": attrs, "text": "\n".join(body), "line": start})
    return blocks


def renderer_command(lang: str) -> list[str] | None:
    """The command that renders `lang`, or None when the tool is not installed."""
    binary = DIAGRAM_RENDERERS[lang][0]
    resolved = shutil.which(binary)
    if not resolved:
        return None
    # npm installs `mmdc.cmd` on Windows, which CreateProcess cannot start直接.
    if resolved.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", resolved]
    return [resolved]


def renderer_argv(lang: str, source: Path, dest: Path) -> list[str] | None:
    """The full command for one render, or None when the tool is not installed."""
    command = renderer_command(lang)
    if command is None:
        return None
    if lang == "mermaid":
        return command + ["-i", str(source), "-o", str(dest)]
    return command + ["-Tsvg", str(source), "-o", str(dest)]


def render_diagram(lang: str, text: str, dest: Path) -> None:
    source = dest.with_suffix(".mmd" if lang == "mermaid" else ".dot")
    argv = renderer_argv(lang, source, dest)
    if argv is None:
        raise SpecError(f"找不到 {DIAGRAM_RENDERERS[lang][0]}")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise SpecError(f"无法写图表缓存 {dest.parent}（{exc}）；源目录需要可写") from None
    try:
        proc = run(argv, check=False)
    except OSError as exc:
        raise SpecError(f"{lang} 渲染器无法启动（{argv[0]}）：{exc}") from None
    if proc.returncode != 0 or not dest.exists():
        detail = (proc.stderr or proc.stdout).strip() or "没有输出文件"
        raise SpecError(f"{lang} 图渲染失败：{detail}")
    source.unlink(missing_ok=True)


def diagram_svg_path(lang: str, text: str, cache_dir: Path) -> Path:
    digest = hashlib.sha1(f"{lang}\n{text}".encode("utf-8")).hexdigest()[:16]
    return cache_dir / f"{digest}.svg"


def prepare_diagrams(inputs: list[Path], base: Path) -> tuple[Path | None, list[str]]:
    """Render every diagram fence to SVG and return (metadata path, warnings)."""
    cache_dir = base / ".pdfgen" / "diagrams"
    entries: dict[str, dict] = {}
    warnings: list[str] = []
    missing: set[str] = set()
    index = 0
    for path in inputs:
        text = path.read_text(encoding="utf-8", errors="replace")
        for block in find_diagram_blocks(text):
            index += 1
            attrs = block["attrs"]
            command = renderer_command(block["lang"])
            if command is None:
                missing.add(block["lang"])
                if attrs.get("caption") or attrs.get("id"):
                    # No renderer: keep the figure (numbering, caption, @fig:
                    # references) and show the source inside it.
                    entries[str(index)] = {
                        "caption": attrs.get("caption", ""),
                        "id": attrs.get("id", ""),
                    }
                continue
            target = diagram_svg_path(block["lang"], block["text"], cache_dir)
            if not target.exists():
                try:
                    render_diagram(block["lang"], block["text"], target)
                except SpecError as exc:
                    raise SpecError(f"{path}:{block['line']} {exc}") from None
            width = attrs.get("width", "")
            if width and not LENGTH_ATTR_RE.match(width):
                raise SpecError(
                    f"{path}:{block['line']} 图宽 {width!r} 不是长度（如 60% / 10cm）"
                )
            label = attrs.get("id", "")
            if label and not LABEL_RE.match(label):
                raise SpecError(f"{path}:{block['line']} 图标签 {label!r} 含非法字符")
            entries[str(index)] = {
                "path": f".pdfgen/diagrams/{target.name}",
                "caption": attrs.get("caption", ""),
                "width": width,
                "id": label,
            }
    for lang in sorted(missing):
        binary, hint = DIAGRAM_RENDERERS[lang]
        warnings.append(f"未安装 {binary}，{lang} 图按源码排出（{hint}）")
    if not entries:
        return None, warnings
    metadata = cache_dir.parent / "diagrams.json"
    try:
        metadata.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: entry for key, entry in entries.items() if any(entry.values())}
        metadata.write_text(
            json.dumps({"pdfgen-diagrams": payload}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise SpecError(f"无法写 {metadata}（{exc}）；源目录需要可写") from None
    return metadata, warnings


FONT_STACKS = {
    "zh": {
        "body": ["Libertinus Serif", "Noto Serif SC", "Source Han Serif SC"],
        "heading": ["Noto Sans SC", "Source Han Sans SC", "DejaVu Sans"],
    },
    "en": {
        "body": ["Libertinus Serif"],
        "heading": ["Noto Sans SC", "DejaVu Sans"],
    },
}


# --------------------------------------------------------------------------- #
# Tiny YAML subset (doc.yml only) — no third-party dependency
# --------------------------------------------------------------------------- #
class SpecError(Exception):
    pass


def _strip_comment(line: str) -> str:
    out, quote = [], None
    prev = ""
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote and prev != "\\":
                quote = None
        else:
            if ch in "\"'":
                quote = ch
                out.append(ch)
            elif ch == "#" and (prev == "" or prev.isspace()):
                break
            else:
                out.append(ch)
        prev = ch
    return "".join(out).rstrip()


def _scalar(text: str) -> object:
    text = text.strip()
    if not text:
        return ""
    if len(text) >= 2 and text[0] == text[-1] and text[0] == '"':
        inner = text[1:-1]
        return (
            inner.replace("\\\\", "\\")
            .replace('\\"', '"')
            .replace("\\n", "\n")
            .replace("\\t", "\t")
        )
    if len(text) >= 2 and text[0] == text[-1] and text[0] == "'":
        return text[1:-1].replace("''", "'")
    low = text.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def parse_simple_yaml(text: str) -> dict:
    """Parse the YAML subset used by doc.yml: maps, lists, scalars, comments."""
    rows = []
    for raw in text.splitlines():
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise SpecError("doc.yml 不支持制表符缩进，请用空格")
        line = _strip_comment(raw)
        if not line.strip() or line.strip() in ("---", "..."):
            continue
        rows.append((len(line) - len(line.lstrip(" ")), line.strip()))
    if not rows:
        return {}

    pos = 0

    def parse_block(indent: int):
        nonlocal pos
        if pos < len(rows) and rows[pos][1].startswith("- "):
            items = []
            while pos < len(rows) and rows[pos][0] == indent and rows[pos][1].startswith("- "):
                items.append(_scalar(rows[pos][1][2:]))
                pos += 1
            return items
        mapping: dict = {}
        while pos < len(rows):
            ind, content = rows[pos]
            if ind < indent:
                break
            if ind > indent:
                raise SpecError(f"doc.yml 缩进不一致: {content!r}")
            if ":" not in content:
                raise SpecError(f"doc.yml 无法解析的行: {content!r}")
            key, _, rest = content.partition(":")
            key = key.strip().strip("\"'")
            pos += 1
            value = rest.strip()
            if value in ("|", "|-", "|+", ">", ">-", ">+"):
                collected = []
                while pos < len(rows) and rows[pos][0] > ind:
                    collected.append(rows[pos][1])
                    pos += 1
                mapping[key] = "\n".join(collected) if value.startswith("|") else " ".join(collected)
            elif value:
                mapping[key] = _scalar(rest)
            elif pos < len(rows) and rows[pos][0] > ind:
                mapping[key] = parse_block(rows[pos][0])
            elif pos < len(rows) and rows[pos][0] == ind and rows[pos][1].startswith("- "):
                mapping[key] = parse_block(ind)
            else:
                mapping[key] = {}
        return mapping

    data = parse_block(rows[0][0])
    if not isinstance(data, dict):
        raise SpecError("doc.yml 顶层必须是映射")
    return data


# --------------------------------------------------------------------------- #
# Process helpers
# --------------------------------------------------------------------------- #
def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True,
        env: dict | None = None) -> subprocess.CompletedProcess:
    e = dict(os.environ)
    e.setdefault("NO_COLOR", "1")
    if env:
        e.update(env)
    proc = subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, capture_output=True,
        text=True, encoding="utf-8", errors="replace", env=e,
    )
    if check and proc.returncode != 0:
        raise SpecError(
            f"命令失败（{proc.returncode}）: {' '.join(cmd)}\n"
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc


def need(binary: str, hint: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise SpecError(f"找不到 {binary}。{hint}")
    return path


# --------------------------------------------------------------------------- #
# Style resolution
# --------------------------------------------------------------------------- #
def flatten(prefix: str, data: dict, out: dict) -> None:
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flatten(path, value, out)
        else:
            out[path] = value


def detect_lang(text: str) -> str:
    cjk = len(CJK_RE.findall(text))
    latin = len(LATIN_WORD_RE.findall(text))
    return "zh" if cjk >= 10 and cjk >= latin * 0.5 else "en"


ENUMS: dict[str, tuple[set[str], str]] = {
    "paper": (PAPERS, "纸张"),
    "palette": (set(PALETTES), "配色"),
    "coverstyle": (COVER_STYLES, "封面样式"),
    "pagenumber": (PAGE_NUMBERS, "页码位置"),
    "header": (HEADERS, "页眉模式"),
    "captionpos": (CAPTION_POS, "题注位置"),
    "codetheme": (CODE_THEMES, "代码主题"),
    "notestyle": ({"footnote", "margin"}, "边注模式"),
}


def coerce(path: str, value: object) -> object:
    typ = KNOBS[path][0]
    if typ == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            low = value.strip().lower()
            if low in ("true", "yes", "on", "1"):
                return True
            if low in ("false", "no", "off", "0"):
                return False
        raise SpecError(f"{path} 需要布尔值，收到 {value!r}")
    if typ == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            raise SpecError(f"{path} 需要整数，收到 {value!r}") from None
    if typ == "fontlist":
        if isinstance(value, list):
            return [str(v) for v in value]
        raw = str(value).strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except ValueError:
                raise SpecError(f"{path} 的字体列表格式不对，收到 {value!r}") from None
            if not isinstance(parsed, list):
                raise SpecError(f"{path} 需要字体数组，收到 {value!r}")
            return [str(v) for v in parsed]
        return [part.strip() for part in raw.split(",") if part.strip()]
    if typ in ("length", "ratio"):
        s = str(value).strip()
        if typ == "length" and not re.fullmatch(r"-?\d+(\.\d+)?(pt|cm|mm|in|em|%|ch)", s):
            raise SpecError(f"{path} 需要长度（如 2.5cm / 11pt），收到 {value!r}")
        if typ == "ratio" and not re.fullmatch(r"\d+(\.\d+)?%", s):
            raise SpecError(f"{path} 需要百分比（如 82%），收到 {value!r}")
        return s
    if typ == "color":
        s = str(value).strip()
        if s == "auto":
            return s
        if not re.fullmatch(r"#?[0-9a-fA-F]{6}", s):
            raise SpecError(f"{path} 需要 6 位十六进制颜色（如 #22645E），收到 {value!r}")
        return s if s.startswith("#") else f"#{s}"
    if typ in ENUMS:
        allowed, label = ENUMS[typ]
        s = str(value).lower()
        if s not in allowed:
            raise SpecError(f"{path} 只能是 {', '.join(sorted(allowed))}，收到 {value!r}")
        return s
    if typ == "numbering":
        s = str(value).strip()
        if s != "none" and not re.fullmatch(r"[0-9A-Za-z.()\-]+", s):
            raise SpecError(f"{path} 需要 Typst numbering 格式（如 1 / 1.1 / (1) / none），收到 {value!r}")
        return s
    if path == "furniture.page-number-format":
        s = str(value).strip()
        if not re.fullmatch(r"[0-9A-Za-z.()\-]+", s):
            raise SpecError(f"{path} 需要 Typst numbering 格式（如 1 / a / i），收到 {value!r}")
        return s
    return str(value)


def resolve_style(kind: str, doc_spec: dict, sets: list[str], lang: str,
                  notes: list[str] | None = None, has_bibliography: bool = False,
                  has_sidenotes: bool = False) -> dict:
    flat = {path: default for path, (_, default) in KNOBS.items()}
    flat["kind"] = kind

    preset = PRESETS.get(kind, {})
    for path, value in preset.items():
        flat[path] = value

    # Accept three shapes: knobs nested under `style:`, knobs grouped at the
    # top level (what `style --write` produces), and flat dotted keys.
    entries: dict = {}
    spec = dict(doc_spec)
    spec.pop("kind", None)
    style_block = spec.pop("style", None)
    if isinstance(style_block, dict):
        flatten("", style_block, entries)
    groups = {path.split(".")[0] for path in KNOBS}
    metadata_keys = ("title", "subtitle", "author", "authors", "date", "org")
    for key, value in spec.items():
        if key in metadata_keys:
            continue
        if key in groups and isinstance(value, dict):
            flatten(key, value, entries)
        elif key in KNOBS:
            entries[key] = value
        else:
            raise SpecError(f"未知样式项 {key!r}（--set 可用 style 子命令查看清单）")
    for key, value in entries.items():
        if key not in KNOBS:
            near = difflib.get_close_matches(key, list(KNOBS), n=3)
            hint = f"，是不是 {', '.join(near)}？" if near else ''
            raise SpecError(f'未知样式项 {key!r}{hint}')
        flat[key] = coerce(key, value)

    for raw in sets:
        if "=" not in raw:
            raise SpecError(f"--set 需要 key=value，收到 {raw!r}")
        key, _, value = raw.partition("=")
        key = key.strip()
        if key not in KNOBS:
            near = difflib.get_close_matches(key, list(KNOBS), n=3)
            hint = f"，是不是 {', '.join(near)}？" if near else ""
            raise SpecError(f"未知样式项 {key!r}{hint}")
        flat[key] = coerce(key, value.strip())

    if flat["text.lang"] == "auto":
        flat["text.lang"] = lang
    stack = FONT_STACKS["zh" if flat["text.lang"].startswith("zh") else "en"]
    if flat["text.font"] == "auto":
        flat["text.font"] = list(stack["body"])
    if flat["text.heading-font"] == "auto":
        flat["text.heading-font"] = list(stack["heading"])

    palette = PALETTES[flat["color.palette"]]
    for key, value in palette.items():
        path = f"color.{key}"
        if flat[path] == "auto":
            flat[path] = value
    if flat["heading.color"] == "auto":
        flat["heading.color"] = flat["color.ink"]

    if flat["cover.enabled"] == "auto":
        flat["cover.enabled"] = kind in ("report", "book", "textbook", "novel")
    if flat["cover.style"] == "auto":
        flat["cover.style"] = "band" if kind != "novel" else "minimal"
    if flat["toc.enabled"] == "auto":
        flat["toc.enabled"] = kind in ("report", "book", "textbook", "novel")
    if flat["toc.depth"] == "auto":
        flat["toc.depth"] = {"textbook": 3, "novel": 1}.get(kind, 2)
    if not isinstance(flat["toc.depth"], int) or not 1 <= flat["toc.depth"] <= 6:
        raise SpecError(f"toc.depth 需要 1–6 的整数，收到 {flat['toc.depth']!r}")
    if flat["toc.title"] == "auto":
        flat["toc.title"] = "目录"
    if flat["furniture.header"] == "auto":
        flat["furniture.header"] = "none"
    if flat["furniture.page-number"] == "auto":
        flat["furniture.page-number"] = "footer-center" if kind != "letter" else "none"
    if flat["novel.dropcap"] == "auto":
        flat["novel.dropcap"] = kind == "novel"
    if flat["novel.chapter-prefix"] == "auto":
        flat["novel.chapter-prefix"] = kind == "novel"
    if flat["cite.enabled"] == "auto":
        flat["cite.enabled"] = has_bibliography
    # `text.lang` is already resolved (auto → the detected language), so a
    # `--set text.lang=en` also moves the citation defaults with it.
    chinese = str(flat["text.lang"]).startswith("zh")
    if flat["cite.style"] == "auto":
        # Article-like documents follow author-date convention; numeric styles
        # are the safe default for reports and books.
        if kind == "article":
            flat["cite.style"] = "apa"
        else:
            flat["cite.style"] = "gb-7714-2015-numeric" if chinese else "ieee"
    if flat["cite.title"] == "auto":
        flat["cite.title"] = "参考文献" if chinese else "References"
    # An explicit `[text]{.sidenote}` is a request for margin space, so it turns
    # margin mode on — unless the author set `note.style` on purpose, in which
    # case the precedence rule in style-knobs.md wins and notes fall back to
    # footnotes.
    note_style_is_explicit = "note.style" in entries or any(
        raw.partition("=")[0].strip() == "note.style" for raw in sets
    )
    if has_sidenotes and not note_style_is_explicit:
        flat["note.style"] = "margin"

    # Typst 0.15 places the next paragraph half a line too high when the
    # paragraph spacing drops below ~4.5pt, which makes lines collide.
    original_spacing = str(flat["text.paragraph-spacing"])
    spacing, clamped = clamp_paragraph_spacing(original_spacing, str(flat["text.size"]))
    flat["text.paragraph-spacing"] = spacing
    if clamped and notes is not None:
        notes.append(
            f"段距 {original_spacing} 低于 4.5pt，已抬到 4.5pt（Typst 0.15 会压字）"
        )

    return nested(flat)


def length_pt(value: str, font_pt: float) -> float | None:
    """Resolve a Typst length to points; `em`/`%` use the given font size."""
    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)(pt|cm|mm|in|em|%)", str(value).strip())
    if not match:
        return None
    amount, unit = float(match.group(1)), match.group(2)
    factor = {
        "pt": 1.0,
        "cm": 72 / 2.54,
        "mm": 72 / 25.4,
        "in": 72.0,
        "em": font_pt,
        "%": font_pt / 100,
    }[unit]
    return amount * factor


def clamp_paragraph_spacing(spacing: str, font_size: str) -> tuple[str, bool]:
    font_pt = length_pt(font_size, 10.0) or 10.0
    spacing_pt = length_pt(spacing, font_pt)
    if spacing_pt is not None and spacing_pt < 4.5:
        return "4.5pt", True
    return spacing, False


def nested(flat: dict) -> dict:
    out: dict = {}
    for path, value in flat.items():
        parts = path.split(".")
        cur = out
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value
    return out


# --------------------------------------------------------------------------- #
# Typst literal emission
# --------------------------------------------------------------------------- #
def tstr(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def tval(typ: str, value: object) -> str:
    if isinstance(value, list):
        return "(" + ", ".join(tstr(str(v)) for v in value) + ",)"
    if typ == "bool":
        return "true" if value else "false"
    if typ == "int":
        return str(int(value))
    if typ == "color":
        return f'rgb("{value}")'
    if typ in ("length", "ratio"):
        # Already validated by coerce(); emit as a Typst literal.
        return str(value)
    if typ in ("numbering", "paper", "palette", "coverstyle",
               "pagenumber", "header", "captionpos", "codetheme", "str"):
        return tstr(str(value))
    return tstr(str(value))


def typst_dict(data: dict, schema: dict, prefix: str = "") -> str:
    lines = []
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            lines.append(f"  {key}: {typst_dict(value, schema, path)},")
        else:
            typ = schema.get(path, ("str", None))[0]
            lines.append(f"  {key}: {tval(typ, value)},")
    return "(\n" + "\n".join(lines) + "\n)"


# --------------------------------------------------------------------------- #
# Metadata
# --------------------------------------------------------------------------- #
def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    try:
        data = parse_simple_yaml(block)
        if isinstance(data, dict):
            return data
    except SpecError:
        pass
    # Lenient fallback: top-level keys only, enough for kind/letter detection.
    found = {}
    for line in block.splitlines():
        match = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if match:
            found[match.group(1)] = _scalar(match.group(2))
    return found


def pandoc_stdout(cmd: list[str], from_fmt: str) -> str:
    proc = run(cmd, check=False)
    if proc.returncode != 0:
        raise SpecError(pandoc_error(proc, from_fmt))
    return proc.stdout


def pandoc_meta(path: Path, from_fmt: str) -> str:
    """Render metadata into a typst `#let meta = (...)` snippet."""
    need("pandoc", "安装：winget install JohnMacFarlane.Pandoc")
    return pandoc_stdout([
        "pandoc", "-f", from_fmt, "-t", "typst",
        f"--template={META_TEMPLATE}", str(path),
    ], from_fmt)


def body_typst(inputs: list[Path], from_fmt: str, kind: str, *,
               note_style: str = "footnote", code_lines: bool = False,
               diagram_metadata: Path | None = None) -> str:
    need("pandoc", "安装：winget install JohnMacFarlane.Pandoc")
    cmd = [
        "pandoc", "-f", from_fmt, "-t", "typst",
        f"--metadata=pdfgen-kind:{kind}",
        f"--metadata=pdfgen-note-style:{note_style}",
        f"--metadata=pdfgen-code-lines:{'yes' if code_lines else 'no'}",
    ]
    if diagram_metadata is not None:
        cmd.append(f"--metadata-file={diagram_metadata}")
    for lua_filter in (DIAGRAM_FILTER, FEATURE_FILTER, LUA_FILTER):
        if not lua_filter.exists():
            raise SpecError(f"缺少 Lua filter {lua_filter}（技能目录不完整，重新安装）")
        cmd += [f"--lua-filter={lua_filter}"]
    cmd += [str(p) for p in inputs]
    return pandoc_stdout(cmd, from_fmt)


def pandoc_error(proc: subprocess.CompletedProcess, from_fmt: str) -> str:
    """Turn pandoc's stderr into something a user can act on."""
    message = (proc.stderr or proc.stdout).strip()
    if "Unknown input format" in message or "is not supported" in message:
        return (
            f"--from 用了 pandoc 不认识的格式：{from_fmt!r}\n{message}\n"
            "提示：默认方言已按 skill 需要钉好，通常不需要传 --from。"
        )
    return f"pandoc 解析失败：\n{message}"


def local_images(body: str, base: Path) -> list[Path]:
    """Image files referenced by `image("…")` that exist on disk.

    URLs and already-absolute references are left alone: they are either not
    Typst paths at all, or come from the style spec rather than the document.
    """
    found: list[Path] = []
    for match in re.finditer(r'image\("([^"]+)"', body):
        raw = match.group(1)
        if _is_external_path(raw):
            continue
        candidate = base / raw
        if candidate.exists():
            resolved = candidate.resolve()
            if resolved not in found:
                found.append(resolved)
    return found


def _is_external_path(raw: str) -> bool:
    """URLs, Windows drive paths, and already-root-relative paths.

    The last case keeps `rewrite_images` idempotent: a path the build has
    already rewritten starts with `/` and must be left alone.
    """
    return bool(
        re.match(r"^[A-Za-z]:[\\/]", raw) or raw.startswith(("/", "\\\\")) or "://" in raw
    )


def project_root(typ_dir: Path, assets: list[Path]) -> Path:
    """The directory Typst gets as `--root`: it must contain the .typ and every asset.

    Typst paths are root-based; Windows drive letters are not valid path
    components, so absolute paths never work and `..` may not escape the root.
    """
    dirs = [str(typ_dir.resolve())] + [str(path.parent) for path in assets]
    try:
        return Path(os.path.commonpath(dirs))
    except ValueError:
        raise SpecError(
            "图片和输出 PDF 不在同一个磁盘上，Typst 无法引用。"
            "把 PDF 输出到图片所在的磁盘，或把图片拷进项目目录。"
        ) from None


def asset_path(target: Path, typ_dir: Path, root: Path) -> str:
    """A Typst-usable path: plain relative when inside the .typ tree, else root-relative.

    Relative paths keep the generated .typ compilable by hand (`typst compile
    file.typ`); root-relative ones only appear when the asset lives outside the
    directory the .typ was written to.
    """
    relative = os.path.relpath(target, typ_dir)
    if not relative.startswith(".."):
        return Path(relative).as_posix()
    return "/" + Path(os.path.relpath(target, root)).as_posix()


def rewrite_images(body: str, base: Path, typ_dir: Path, root: Path) -> str:
    """Point every existing local image at a path Typst can resolve."""

    def replace(match: re.Match) -> str:
        raw = match.group(1)
        if _is_external_path(raw):
            return match.group(0)
        candidate = base / raw
        if not candidate.exists():
            # Keep the original text: it may be a code sample, not an asset.
            return match.group(0)
        reference = asset_path(candidate.resolve(), typ_dir, root)
        return f'image("{reference}"'

    return re.sub(r'image\("([^"]+)"', replace, body)


# --------------------------------------------------------------------------- #
# Composition
# --------------------------------------------------------------------------- #
def template_source() -> str:
    parts = []
    for path in sorted(TEMPLATE_DIR.glob("*.typ")):
        if path.name == "meta.typ":
            continue
        parts.append(f"// ---- {path.name} " + "-" * max(0, 60 - len(path.name)))
        parts.append(path.read_text(encoding="utf-8").rstrip())
    return "\n\n".join(parts)


def typst_args(root: Path | None = None) -> list[str]:
    """Options every typst invocation needs: vendored packages and project root."""
    args: list[str] = []
    if VENDOR_PACKAGES.exists():
        args += ["--package-path", str(VENDOR_PACKAGES)]
    if root:
        args += ["--root", str(root)]
    return args


def root_from_typ(typ: Path) -> Path | None:
    """Recover the project root a generated .typ was built with."""
    try:
        head = typ.read_text(encoding="utf-8", errors="replace")[:2000]
    except OSError:
        return None
    match = re.search(r"^// pdfgen-root: (.+)$", head, re.M)
    return Path(match.group(1).strip()) if match else None


def compose(typ_path: Path, *, meta_ty: str, letter_ty: str, bib_ty: str, style: dict,
            body: str, root: Path | None = None) -> None:
    header = (
        "// Generated by the pdf-generation skill. Rebuilding overwrites this\n"
        "// file; to hand-edit it, build once, edit, then rerun with --keep-typ.\n"
        "// Everything here is self-contained, so `typst compile <this file>`\n"
        "// reproduces the PDF without the skill.\n"
    )
    if root is not None and root.resolve() != typ_path.parent.resolve():
        # Only recorded when assets live outside the .typ's own directory: that
        # is when paths are root-relative and `typst compile` needs --root.
        header += f"// pdfgen-root: {root.as_posix()}\n"
    style_lit = typst_dict(style, KNOBS)
    text = "\n".join([
        header,
        template_source(),
        "",
        meta_ty.strip(),
        "",
        letter_ty,
        "",
        bib_ty,
        "",
        f"#let style = {style_lit}",
        "",
        "#show: doc.with(meta: meta + (letter: letter, bib: bib), style: style)",
        "",
        body.strip(),
        "",
        "#context [#metadata(here().page())<pdfgen-pages>]",
        "",
    ])
    typ_path.write_text(text, encoding="utf-8")


LETTER_FIELDS = ("from", "to", "date", "subject", "salutation", "closing", "signature")


def typst_plain(text: object) -> str:
    """Plain-text metadata as Typst content, keeping line breaks meaningful."""
    lines = [line for line in str(text).replace("\r\n", "\n").split("\n")]
    parts = [f"#text({tstr(line.strip())})" for line in lines if line.strip()]
    return "[" + "#linebreak()".join(parts) + "]"


def bib_snippet(path: str) -> str:
    """Describe the bibliography so the template can emit `#bibliography(...)`."""
    if not path:
        return '#let bib = (\n  path: "",\n  has-path: "no",\n)'
    return (
        "#let bib = (\n"
        f"  path: {tstr(path)},\n"
        '  has-path: "yes",\n'
        ")"
    )


def bibliography_field(frontmatter: dict) -> str:
    value = frontmatter.get("bibliography")
    if value is None:
        return ""
    if isinstance(value, list):
        raise SpecError("frontmatter 的 bibliography 只支持一个文件（收到列表）")
    return str(value).strip()


def resolve_bibliography(frontmatter: dict, base: Path) -> Path | None:
    raw = bibliography_field(frontmatter)
    if not raw:
        return None
    path = Path(raw)
    candidate = path if path.is_absolute() else base / path
    if not candidate.exists():
        raise SpecError(f"找不到书目文件 {raw}（按 {base} 解析）")
    return candidate.resolve()


def resolve_csl(style: str, base: Path) -> Path | None:
    """A `cite.style` that names a CSL file rather than a built-in style."""
    if not style or style == "auto":
        return None
    looks_like_file = (
        Path(style).suffix.lower() == ".csl" or "/" in style or "\\" in style
    )
    if not looks_like_file:
        return None
    candidate = Path(style)
    path = candidate if candidate.is_absolute() else base / candidate
    if not path.exists():
        raise SpecError(f"找不到 CSL 样式文件 {style}（按 {base} 解析）")
    return path.resolve()


def letter_snippet(frontmatter: dict) -> str:
    data = frontmatter.get("letter")
    data = data if isinstance(data, dict) else {}
    rows = ["#let letter = ("]
    for field in LETTER_FIELDS:
        value = data.get(field)
        if value is None or str(value).strip() == "":
            rows.append(f"  {field}: [],")
            rows.append(f'  has-{field}: "no",')
        else:
            rows.append(f"  {field}: {typst_plain(value)},")
            rows.append(f'  has-{field}: "yes",')
    rows.append(")")
    return "\n".join(rows)


# --------------------------------------------------------------------------- #
# Rendering and self-check
# --------------------------------------------------------------------------- #
def page_count(typ: Path, root: Path | None = None) -> int:
    proc = run(["typst", "eval", *typst_args(root), "query(<pdfgen-pages>)", "--in", str(typ)],
               check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return 0
    try:
        data = json.loads(proc.stdout)
        return int(data[0]["value"]) if data else 0
    except (ValueError, KeyError, IndexError):
        return 0


def parse_warnings(stderr: str) -> list[str]:
    out, current = [], []
    for line in stderr.splitlines():
        if line.startswith("warning:"):
            if current:
                out.append(" ".join(current).strip())
            current = [line.strip()]
        elif line.startswith("error:"):
            if current:
                out.append(" ".join(current).strip())
            current = [line.strip()]
        elif current and line.strip() and not line.startswith("  "):
            current.append(line.strip())
        elif current and line.startswith("  = "):
            current.append(line.strip())
    if current:
        out.append(" ".join(current).strip())
    return out


def pick_samples(total: int, mode: str) -> list[int]:
    if total <= 0:
        return []
    if mode == "all":
        return list(range(1, total + 1))
    if total == 1:
        return [1]
    # Front matter (cover, table of contents) occupies the first pages, so a
    # page at 60% of the document lands in the body; short documents fall back
    # to their last page.
    page = min(total, max(3, round(total * 0.6)))
    return [page]


def render_samples(typ: Path, samples: list[int], preview: Path,
                   ppi: int = 100, root: Path | None = None) -> list[Path]:
    if not samples:
        return []
    preview.mkdir(parents=True, exist_ok=True)
    pages = ",".join(str(p) for p in samples)
    run([
        "typst", "compile", *typst_args(root), "--format", "png", f"--ppi={ppi}",
        "--pages", pages, str(typ), str(preview / "p{p}.png"),
    ])
    return [preview / f"p{p}.png" for p in samples if (preview / f"p{p}.png").exists()]


def build_one(inputs: list[Path], out_pdf: Path | None, kind: str | None,
              sets: list[str], doc_path: Path | None, from_fmt: str,
              check_mode: str, keep_typ: bool, quiet: bool) -> dict:
    started = time.time()
    need("typst", "安装：winget install Typst.Typst 或 scoop install typst")
    need("pandoc", "安装：winget install JohnMacFarlane.Pandoc")
    for path in inputs:
        if not path.exists():
            raise SpecError(f"找不到输入文件 {path}")

    first = inputs[0]
    doc_spec: dict = {}
    spec_path = doc_path or first.with_suffix(".doc.yml")
    if spec_path.exists():
        doc_spec = parse_simple_yaml(spec_path.read_text(encoding="utf-8"))
    elif doc_path:
        raise SpecError(f"找不到样式文件 {doc_path}")

    fm = read_frontmatter(first)
    chosen = kind or fm.get("kind") or doc_spec.get("kind") or "report"
    if chosen not in KINDS:
        raise SpecError(f"未知 Kind {chosen!r}，可选：{', '.join(KINDS)}")

    source_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in inputs)
    lang = detect_lang(source_text)
    bib_path = resolve_bibliography(fm, first.parent)
    has_notes, _, _ = inspect_sidenotes(source_text)
    notes: list[str] = []
    style = resolve_style(str(chosen), doc_spec, sets, lang, notes,
                          has_bibliography=bib_path is not None,
                          has_sidenotes=has_notes)
    # Footnotes only reach the margin when margin mode is on, so they only need
    # checking then.
    _, long_notes, crowded = inspect_sidenotes(
        source_text, include_footnotes=style["note"]["style"] == "margin"
    )

    out_pdf = out_pdf or first.with_suffix(".pdf")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    typ_path = out_pdf.with_suffix(".typ")

    if keep_typ and typ_path.exists():
        body_note = "复用已有 .typ"
        root = root_from_typ(typ_path)
        diagram_warnings: list[str] = []
    else:
        body_note = "pandoc 解析"
        meta = pandoc_meta(first, from_fmt)
        diagram_filter, diagram_warnings = prepare_diagrams(inputs, first.parent)
        raw_body = body_typst(inputs, from_fmt, str(chosen),
                              note_style=str(style["note"]["style"]),
                              code_lines=bool(style["code"]["line-numbers"]),
                              diagram_metadata=diagram_filter)
        if "#ref(<eq:" in raw_body and style["math"]["numbering"] == "none":
            raise SpecError(
                "正文引用了公式（@eq:），但公式没有编号，Typst 无法生成引用。\n"
                "用 --set math.numbering=(1) 打开公式编号，或在 doc.yml 里设 math.numbering。"
            )
        images = local_images(raw_body, first.parent)
        csl_path = resolve_csl(str(style["cite"]["style"]), first.parent)
        assets = images + [p for p in (bib_path, csl_path) if p]
        root = project_root(typ_path.parent, assets)
        if csl_path:
            # Typst wants a root-relative or sibling path, never a drive path.
            style["cite"]["style"] = asset_path(csl_path, typ_path.parent, root)
        body = rewrite_images(raw_body, first.parent, typ_path.parent, root)
        bib_ty = bib_snippet(
            asset_path(bib_path, typ_path.parent, root) if bib_path else ""
        )
        compose(typ_path, meta_ty=meta, letter_ty=letter_snippet(fm), bib_ty=bib_ty,
                style=style, body=body, root=root)

    proc = run(["typst", "compile", *typst_args(root), str(typ_path), str(out_pdf)], check=False)
    warnings = parse_warnings(proc.stderr)
    warnings.extend(diagram_warnings)
    if proc.returncode != 0:
        raise SpecError(f"Typst 编译失败：\n{proc.stderr.strip()}")
    for length in long_notes:
        warnings.append(f"边注过长（{length} 字），可能压住其它边注或溢出页面；建议拆短或改成脚注")
    if crowded:
        warnings.append(f"{crowded} 处相邻边注间距过近，页边可能重叠；建议拉开距离或合并")

    total = page_count(typ_path, root)
    samples = pick_samples(total, check_mode) if check_mode != "none" else []
    if check_mode == "sample" and warnings and total > 1:
        extra = [1, 2]
        samples = sorted(set(samples + extra))
    preview = out_pdf.parent / ".pdfgen" / out_pdf.stem
    try:
        rendered = render_samples(typ_path, samples, preview, root=root)
    except SpecError as exc:
        warnings.append(f"抽页渲染失败：{exc}")
        rendered = []

    result = {
        "pdf": str(out_pdf),
        "typ": str(typ_path),
        "kind": chosen,
        "lang": lang,
        "pages": total,
        "samples": [str(p) for p in rendered],
        "warnings": warnings,
        "notes": notes,
        "source": body_note,
        "duration": round(time.time() - started, 2),
    }
    if not quiet:
        print(f"PDF   {out_pdf}  ({total} 页, {result['duration']}s)")
        print(f"TYP   {typ_path}")
        print(f"Kind  {chosen}   语言 {lang}   纸张 {style['page']['paper']}")
        for note in notes:
            print(f"i     {note}")
        for warning in warnings:
            print(f"!     {warning}")
        for sample in rendered:
            print(f"抽检  {sample}")
    return result


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_detect(args) -> int:
    inputs = [Path(p) for p in args.inputs]
    texts = []
    for path in inputs:
        if not path.exists():
            raise SpecError(f"找不到输入文件 {path}")
        texts.append(path.read_text(encoding="utf-8", errors="replace"))
    joined = "\n".join(texts)
    cjk = len(CJK_RE.findall(joined))
    words = len(LATIN_WORD_RE.findall(joined)) + cjk
    heading_lines = [ln for ln in joined.splitlines() if re.match(r"^(#{1,6})\s+\S", ln)]
    h1 = sum(1 for ln in heading_lines if ln.startswith("# ") and not ln.startswith("## "))
    fm = read_frontmatter(inputs[0])
    letterish = any(k in fm for k in ("letter", "from", "to", "recipient"))
    suggested = fm.get("kind")
    if not suggested:
        if letterish:
            suggested = "letter"
        elif h1 >= 4 and words > 6000:
            suggested = "book"
        else:
            suggested = "report"
    info = {
        "inputs": [str(p) for p in inputs],
        "suggested_kind": suggested,
        "lang": detect_lang(joined),
        "cjk_chars": cjk,
        "words": words,
        "headings": {"h1": h1, "total": len(heading_lines)},
        "frontmatter": sorted(fm.keys()),
        "features": {
            "table": bool(re.search(r"^\s*\|.*\|\s*$", joined, re.M)),
            "code": "```" in joined,
            "math": bool(re.search(r"\$[^$\n]+\$", joined)),
            "image": bool(re.search(r"!\[[^\]]*\]\(", joined)),
            "fenced_div": bool(re.search(r"^:::", joined, re.M)),
            "footnote": bool(re.search(r"\[\^[^\]]+\]", joined)),
            "task_list": bool(re.search(r"^\s*- \[[ x]\]", joined, re.M)),
        },
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def cmd_build(args) -> int:
    # `build something.typ` is treated as "compile and check this file", which
    # is what people mean after hand-editing an intermediate.
    if len(args.inputs) == 1 and args.inputs[0].lower().endswith(".typ"):
        ns = argparse.Namespace(typ=args.inputs[0], check="all" if args.check == "all" else "sample")
        return cmd_check(ns)
    inputs = [Path(p) for p in args.inputs]
    result = build_one(
        inputs, Path(args.output) if args.output else None, args.kind,
        args.set or [], Path(args.doc) if args.doc else None,
        args.from_format, args.check, args.keep_typ, args.quiet,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_style(args) -> int:
    inputs = [Path(p) for p in args.inputs]
    for path in inputs:
        if not path.exists():
            raise SpecError(f"找不到输入文件 {path}")
    doc_spec = {}
    if args.doc:
        doc_spec = parse_simple_yaml(Path(args.doc).read_text(encoding="utf-8"))
    fm = read_frontmatter(inputs[0])
    kind = args.kind or doc_spec.get("kind") or fm.get("kind") or "report"
    source_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in inputs)
    lang = detect_lang(source_text)
    has_notes, _, _ = inspect_sidenotes(source_text)
    style = resolve_style(str(kind), doc_spec, args.set or [], lang,
                          has_bibliography=bibliography_field(fm) != "",
                          has_sidenotes=has_notes)
    text = to_yaml(style)
    if args.write:
        target = Path(args.write)
        target.write_text(text, encoding="utf-8")
        print(f"写入 {target}")
    else:
        print(text)
    return 0


def _yaml_scalar(value: object) -> str:
    """Quote only what a YAML reader could misread."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    safe = re.fullmatch(r"[A-Za-z0-9_.\-/]+", text) is not None
    reserved = text.lower() in {"true", "false", "yes", "no", "on", "off", "null", "none", "~"}
    if text and safe and not reserved:
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_yaml(data: dict, indent: int = 0) -> str:
    pad = " " * indent
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            lines.append(to_yaml(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{pad}{key}:")
            for item in value:
                lines.append(f"{pad}  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{pad}{key}: {_yaml_scalar(value)}")
    return "\n".join(lines)


def cmd_check(args) -> int:
    typ = Path(args.typ)
    if not typ.exists():
        raise SpecError(f"找不到 {typ}")
    root = root_from_typ(typ)
    proc = run(["typst", "compile", *typst_args(root), str(typ), str(typ.with_suffix(".pdf"))],
               check=False)
    warnings = parse_warnings(proc.stderr)
    if proc.returncode != 0:
        print(proc.stderr.strip(), file=sys.stderr)
        return 1
    total = page_count(typ, root)
    samples = pick_samples(total, args.check)
    preview = typ.parent / ".pdfgen" / typ.stem
    if preview.exists():
        shutil.rmtree(preview, ignore_errors=True)
    rendered = render_samples(typ, samples, preview, root=root)
    print(f"页数 {total}")
    for warning in warnings:
        print(f"! {warning}")
    for sample in rendered:
        print(f"抽检 {sample}")
    return 0


def cmd_doctor(args) -> int:
    ok = True
    for binary, hint in (
        ("typst", "winget install Typst.Typst"),
        ("pandoc", "winget install JohnMacFarlane.Pandoc"),
    ):
        path = shutil.which(binary)
        if path:
            version = run([binary, "--version"], check=False).stdout.splitlines()
            print(f"[ok]   {binary}: {version[0] if version else path}")
        else:
            ok = False
            print(f"[fail] 缺少 {binary} — {hint}")
    if not ok:
        return 1
    fonts = run(["typst", "fonts"], check=False).stdout.splitlines()
    for font in ("Libertinus Serif", "New Computer Modern Math", "DejaVu Sans Mono"):
        mark = "ok  " if font in fonts else "warn"
        print(f"[{mark}] 内置字体 {font}")
    for font in ("Noto Serif SC", "Noto Sans SC"):
        mark = "ok  " if font in fonts else "warn"
        print(f"[{mark}] 中文字体 {font}（缺失时中文会用后备字体）")
    for lang, (binary, hint) in DIAGRAM_RENDERERS.items():
        if shutil.which(binary):
            print(f"[ok  ] 图表渲染器 {binary}（{lang}）")
        else:
            print(f"[warn] 缺少 {binary}（可选：{hint}）；{lang} 图按源码排出")
    tmp = Path(tempfile.mkdtemp(prefix="pdfgen-doctor-", dir=Path.cwd()))
    try:
        if VENDOR_PACKAGES.exists():
            probe = tmp / "chess.typ"
            probe.write_text(
                f'#import "@preview/staunton:{STAUNTON_VERSION}": board\n'
                '#board("8/8/8/8/8/8/8/8")\n',
                encoding="utf-8",
            )
            proc = run(["typst", "compile", *typst_args(), str(probe), str(tmp / "chess.pdf")],
                       check=False)
            if proc.returncode == 0:
                print(f"[ok  ] 内联包 staunton {STAUNTON_VERSION}（棋谱可用，离线）")
            else:
                ok = False
                first = (proc.stderr.strip().splitlines() or [""])[0]
                print(f"[fail] 内联包 staunton 无法 import：{first}")
        else:
            ok = False
            print("[fail] 缺少 vendor/typst-packages，棋谱围栏不可用（见 INSTALL.md）")
        styles = ("gb-7714-2015-numeric", "ieee", "apa")
        (tmp / "doctor.bib").write_text(
            "@book{doctor, author = {Doe, John}, title = {T}, year = {2024},\n"
            " publisher = {P}}\n",
            encoding="utf-8",
        )
        missing = []
        for style in styles:
            probe = tmp / f"csl-{style}.typ"
            probe.write_text(
                f'#bibliography("doctor.bib", style: "{style}")\n#cite(<doctor>)\n',
                encoding="utf-8",
            )
            proc = run(
                ["typst", "compile", *typst_args(), str(probe), str(tmp / f"{style}.pdf")],
                check=False,
            )
            if proc.returncode != 0:
                first = (proc.stderr.strip().splitlines() or [""])[0]
                missing.append(f"{style}（{first}）")
        if missing:
            ok = False
            print(f"[fail] CSL 样式不可用：{'; '.join(missing)}")
        else:
            print(f"[ok  ] CSL 样式 {' / '.join(styles)}")
        sample = tmp / "doctor.md"
        sample.write_text("# 自检\n\n这是一段中文自检文字。\n", encoding="utf-8")
        try:
            result = build_one([sample], tmp / "doctor.pdf", "report", [],
                               None, FROM_FORMAT, "none", False, True)
            print(f"[ok]   模板自检 {result['pages']} 页")
        except SpecError as exc:
            ok = False
            print(f"[fail] 模板自检：{exc}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="build_pdf.py",
        description="Markdown -> PDF（pandoc 解析 + Typst 排版）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("detect", help="检查源文件并输出 Clarify 所需事实")
    p.add_argument("inputs", nargs="+")
    p.set_defaults(func=cmd_detect)

    p = sub.add_parser("build", help="生成 PDF")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--output")
    p.add_argument("--kind", choices=KINDS)
    p.add_argument("--set", action="append", metavar="KEY=VALUE")
    p.add_argument("--doc", help="Style spec 文件（默认 <首个输入文件>.doc.yml）")
    p.add_argument("--from", dest="from_format", default=FROM_FORMAT,
                   help=f"Markdown 方言（默认：{FROM_FORMAT}）")
    p.add_argument("--check", choices=("none", "sample", "all"), default="sample")
    p.add_argument("--keep-typ", action="store_true", help="不重新生成 .typ，直接编译")
    p.add_argument("--json", action="store_true")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("style", help="打印或写出解析后的 Style spec")
    p.add_argument("inputs", nargs="+")
    p.add_argument("--kind", choices=KINDS)
    p.add_argument("--set", action="append", metavar="KEY=VALUE")
    p.add_argument("--doc")
    p.add_argument("--write", metavar="PATH")
    p.set_defaults(func=cmd_style)

    p = sub.add_parser("check", help="只检查已有的 .typ")
    p.add_argument("typ")
    p.add_argument("--check", choices=("sample", "all"), default="sample")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("doctor", help="检查 pandoc / typst / 字体")
    p.set_defaults(func=cmd_doctor)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SpecError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
