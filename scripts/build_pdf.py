#!/usr/bin/env python3
"""pdf-generation: Markdown -> PDF, parsed by pandoc, laid out by Typst.

The bundled template in ``template/`` owns every layout decision.  pandoc is
used only as a Markdown parser (``-f gfm -t typst``); Typst renders the PDF.

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

KINDS = ("report", "article", "letter", "note", "book", "textbook", "novel")

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
    "page.columns": ("int", 1),
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
    "float.numbering": ("numbering", "1.1"),
    "float.figure-width": ("ratio", "82%"),
    # code -------------------------------------------------------------------
    "code.theme": ("codetheme", "default"),
    "code.size": ("length", "9pt"),
    "code.header": ("bool", True),
    # math -------------------------------------------------------------------
    "math.numbering": ("numbering", "none"),
    # semantic blocks --------------------------------------------------------
    "semantic.numbering": ("numbering", "1.1"),
    # kind specific ----------------------------------------------------------
    "novel.dropcap": ("bool", "auto"),
    "novel.chapter-prefix": ("bool", "auto"),
    "letter.sender": ("str", ""),
    "letter.recipient": ("str", ""),
    "letter.date": ("str", ""),
    "letter.subject": ("str", ""),
    "letter.salutation": ("str", ""),
    "letter.closing": ("str", ""),
    "letter.signature": ("str", ""),
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
        "semantic.numbering": "1.1",
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
    if low in ("null", "~", "none"):
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
    return "zh" if cjk >= max(20, latin * 0.2) else "en"


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
            raise SpecError(f"{path} 需要整数，收到 {value!r}")
    if typ == "fontlist":
        if isinstance(value, list):
            return [str(v) for v in value]
        return [part.strip() for part in str(value).split(",") if part.strip()]
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
    if typ == "paper":
        s = str(value).lower()
        if s not in PAPERS:
            raise SpecError(f"{path} 只能是 {', '.join(sorted(PAPERS))}，收到 {value!r}")
        return s
    if typ == "palette":
        s = str(value).lower()
        if s not in PALETTES:
            raise SpecError(f"{path} 只能是 {', '.join(PALETTES)}，收到 {value!r}")
        return s
    if typ == "coverstyle":
        s = str(value).lower()
        if s not in COVER_STYLES:
            raise SpecError(f"{path} 只能是 {', '.join(sorted(COVER_STYLES))}，收到 {value!r}")
        return s
    if typ == "pagenumber":
        s = str(value).lower()
        if s not in PAGE_NUMBERS:
            raise SpecError(f"{path} 只能是 {', '.join(sorted(PAGE_NUMBERS))}，收到 {value!r}")
        return s
    if typ == "header":
        s = str(value).lower()
        if s not in HEADERS:
            raise SpecError(f"{path} 只能是 {', '.join(sorted(HEADERS))}，收到 {value!r}")
        return s
    if typ == "captionpos":
        s = str(value).lower()
        if s not in CAPTION_POS:
            raise SpecError(f"{path} 只能是 top 或 bottom，收到 {value!r}")
        return s
    if typ == "codetheme":
        s = str(value).lower()
        if s not in CODE_THEMES:
            raise SpecError(f"{path} 只能是 default 或 none，收到 {value!r}")
        return s
    if typ == "numbering":
        s = str(value).strip()
        if s != "none" and not re.fullmatch(r"[0-9A-Za-z.()（）第章]+", s):
            raise SpecError(f"{path} 需要 Typst numbering 格式（如 1.1 / 1.a / none），收到 {value!r}")
        return s
    return str(value)


def resolve_style(kind: str, doc_spec: dict, sets: list[str], lang: str) -> dict:
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
        flat[key] = coerce(key, value)

    for raw in sets:
        if "=" not in raw:
            raise SpecError(f"--set 需要 key=value，收到 {raw!r}")
        key, _, value = raw.partition("=")
        key = key.strip()
        if key not in KNOBS:
            import difflib
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

    # Typst 0.15 places the next paragraph half a line too high when the
    # paragraph spacing is (near) zero, which makes the lines collide.
    if re.fullmatch(r"0(\.0+)?\s*(pt|em|cm|mm|in)", str(flat["text.paragraph-spacing"])):
        flat["text.paragraph-spacing"] = "4.5pt"

    return nested(flat)


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


def pandoc_meta(path: Path, from_fmt: str) -> str:
    """Render metadata into a typst `#let meta = (...)` snippet."""
    need("pandoc", "安装：winget install JohnMacFarlane.Pandoc")
    proc = run([
        "pandoc", "-f", from_fmt, "-t", "typst",
        f"--template={META_TEMPLATE}", str(path),
    ])
    return proc.stdout


def body_typst(inputs: list[Path], from_fmt: str, kind: str) -> str:
    need("pandoc", "安装：winget install JohnMacFarlane.Pandoc")
    cmd = ["pandoc", "-f", from_fmt, "-t", "typst", f"--metadata=pdfgen-kind:{kind}"]
    if LUA_FILTER.exists():
        cmd += [f"--lua-filter={LUA_FILTER}"]
    cmd += [str(p) for p in inputs]
    return run(cmd).stdout


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


def compose(typ_path: Path, meta_snippet: str, letter_ty: str, style: dict, body: str) -> None:
    header = (
        "// Generated by the pdf-generation skill. Do not edit: regenerate with\n"
        "// scripts/build_pdf.py. Everything below is self-contained so this file\n"
        "// can be compiled directly:  typst compile <this file>\n"
    )
    style_lit = typst_dict(style, KNOBS)
    text = "\n".join([
        header,
        template_source(),
        "",
        meta_snippet.strip(),
        "",
        letter_ty,
        "",
        f"#let style = {style_lit}",
        "",
        "#show: doc.with(meta: meta + (letter: letter), style: style)",
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
def page_count(typ: Path) -> int:
    proc = run(["typst", "eval", "query(<pdfgen-pages>)", "--in", str(typ)], check=False)
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
    # One representative content page: the middle of the document, never the
    # cover.  The cover is only sampled when the check widens.
    middle = max(2, min(total, round(total * 0.5)))
    return [middle]


def render_samples(typ: Path, total: int, samples: list[int], preview: Path,
                   ppi: int = 100) -> list[Path]:
    if not samples:
        return []
    preview.mkdir(parents=True, exist_ok=True)
    pages = ",".join(str(p) for p in samples)
    run([
        "typst", "compile", "--format", "png", f"--ppi={ppi}",
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
    chosen = kind or doc_spec.get("kind") or fm.get("kind") or "report"
    if chosen not in KINDS:
        raise SpecError(f"未知 Kind {chosen!r}，可选：{', '.join(KINDS)}")

    lang = detect_lang("\n".join(p.read_text(encoding="utf-8", errors="replace") for p in inputs))
    style = resolve_style(str(chosen), doc_spec, sets, lang)

    out_pdf = out_pdf or first.with_suffix(".pdf")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    typ_path = out_pdf.with_suffix(".typ")

    if keep_typ and typ_path.exists():
        body_note = "复用已有 .typ"
    else:
        body_note = "pandoc 解析"
        meta = pandoc_meta(first, from_fmt)
        body = body_typst(inputs, from_fmt, str(chosen))
        compose(typ_path, meta, letter_snippet(fm), style, body)

    proc = run(["typst", "compile", str(typ_path), str(out_pdf)], check=False)
    warnings = parse_warnings(proc.stderr)
    if proc.returncode != 0:
        raise SpecError(f"Typst 编译失败：\n{proc.stderr.strip()}")

    total = page_count(typ_path)
    samples = pick_samples(total, check_mode) if check_mode != "none" else []
    if check_mode == "sample" and warnings and total > 1:
        extra = [1, 2]
        samples = sorted(set(samples + extra))
    preview = out_pdf.parent / ".pdfgen" / out_pdf.stem
    try:
        rendered = render_samples(typ_path, total, samples, preview)
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
        "duration": round(time.time() - started, 2),
        "notes": body_note,
    }
    if not quiet:
        print(f"PDF   {out_pdf}  ({total} 页, {result['duration']}s)")
        print(f"TYP   {typ_path}")
        print(f"Kind  {chosen}   语言 {lang}   纸张 {style['page']['paper']}")
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
    lang = detect_lang("\n".join(p.read_text(encoding="utf-8", errors="replace") for p in inputs))
    style = resolve_style(str(kind), doc_spec, args.set or [], lang)
    text = to_yaml(style)
    if args.write:
        target = Path(args.write)
        target.write_text(text, encoding="utf-8")
        print(f"写入 {target}")
    else:
        print(text)
    return 0


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
                lines.append(f"{pad}  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{pad}{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{pad}{key}: {value}")
    return "\n".join(lines)


def cmd_check(args) -> int:
    typ = Path(args.typ)
    if not typ.exists():
        raise SpecError(f"找不到 {typ}")
    proc = run(["typst", "compile", str(typ), str(typ.with_suffix(".pdf"))], check=False)
    warnings = parse_warnings(proc.stderr)
    if proc.returncode != 0:
        print(proc.stderr.strip(), file=sys.stderr)
        return 1
    total = page_count(typ)
    samples = pick_samples(total, args.check)
    preview = typ.parent / ".pdfgen" / typ.stem
    rendered = render_samples(typ, total, samples, preview)
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
    tmp = Path(tempfile.mkdtemp(prefix="pdfgen-doctor-", dir=Path.cwd()))
    try:
        sample = tmp / "doctor.md"
        sample.write_text("# 自检\n\n这是一段中文自检文字。\n", encoding="utf-8")
        try:
            result = build_one([sample], tmp / "doctor.pdf", "report", [],
                               None, "gfm", "none", False, True)
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
    p.add_argument("--doc", help="Style spec 文件（默认 <stdin>.doc.yml）")
    p.add_argument("--from", dest="from_format", default="gfm+fenced_divs")
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
