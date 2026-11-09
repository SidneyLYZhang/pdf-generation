"""End-to-end CLI tests: build real documents.

Skipped automatically when typst or pandoc is missing.
"""

from __future__ import annotations

import contextlib
import base64
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_pdf as bp  # noqa: E402

HAVE_DEPS = bool(shutil.which("typst") and shutil.which("pandoc"))


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = bp.main(argv)
    return code, out.getvalue(), err.getvalue()


@unittest.skipUnless(HAVE_DEPS, "需要 typst 与 pandoc")
class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix=".pdfgen-test-", dir=str(ROOT)))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, source: str, *extra: str) -> tuple[int, str, str]:
        out = self.tmp / (Path(source).stem + ".pdf")
        return run_cli(
            ["build", str(ROOT / "examples" / source), "-o", str(out), "--check", "none", *extra]
        )

    def test_report_builds_with_cover_and_toc(self):
        code, out, err = self.build("report.md")
        self.assertEqual(code, 0, err)
        pdf = self.tmp / "report.pdf"
        self.assertTrue(pdf.exists())
        typ = pdf.with_suffix(".typ")
        self.assertTrue(typ.exists())
        text = typ.read_text(encoding="utf-8")
        self.assertIn("#show: doc.with", text)
        self.assertIn("pdfgen-pages", text)
        self.assertGreater(bp.page_count(typ), 1)
        self.assertIn("PDF", out)

    def test_set_override_reaches_the_generated_typ(self):
        code, _, err = self.build("report.md", "--set", "text.size=9pt")
        self.assertEqual(code, 0, err)
        text = (self.tmp / "report.typ").read_text(encoding="utf-8")
        self.assertIn("size: 9pt,", text)

    def test_unknown_knob_fails_with_hint(self):
        code, _, err = self.build("report.md", "--set", "page.margins=2cm")
        self.assertEqual(code, 1)
        self.assertIn("未知样式项", err)

    def test_letter_uses_frontmatter_fields(self):
        code, _, err = self.build("letter.md", "--kind", "letter")
        self.assertEqual(code, 0, err)
        text = (self.tmp / "letter.typ").read_text(encoding="utf-8")
        self.assertIn("示例公司", text)
        self.assertIn("#linebreak()", text)
        self.assertIn('has-from: "yes"', text)

    def test_textbook_maps_semantic_blocks(self):
        code, _, err = self.build("textbook.md")
        self.assertEqual(code, 0, err)
        text = (self.tmp / "textbook.typ").read_text(encoding="utf-8")
        self.assertIn("#thm(", text)
        self.assertIn("#defn(", text)
        self.assertIn("#exercise", text)

    def test_novel_wraps_chapter_opening(self):
        code, _, err = self.build("novel.md")
        self.assertEqual(code, 0, err)
        text = (self.tmp / "novel.typ").read_text(encoding="utf-8")
        self.assertIn("#dropcap(", text)
        self.assertIn("chapter-prefix: true", text)

    def test_style_write_roundtrip(self):
        spec = self.tmp / "report.doc.yml"
        code, _, err = run_cli(["style", str(ROOT / "examples/report.md"), "--write", str(spec)])
        self.assertEqual(code, 0, err)
        self.assertTrue(spec.exists())
        code, _, err = self.build("report.md", "--doc", str(spec))
        self.assertEqual(code, 0, err)

    def test_multi_file_book_builds(self):
        out = self.tmp / "book.pdf"
        code, _, err = run_cli([
            "build",
            str(ROOT / "examples/book/book.md"),
            str(ROOT / "examples/book/ch01.md"),
            str(ROOT / "examples/book/ch02.md"),
            "-o", str(out), "--check", "none",
        ])
        self.assertEqual(code, 0, err)
        self.assertTrue(out.exists())
        self.assertGreater(bp.page_count(out.with_suffix(".typ")), 2)

    def test_detect_reports_json(self):
        code, out, err = run_cli(["detect", str(ROOT / "examples/report.md")])
        self.assertEqual(code, 0, err)
        self.assertIn('"suggested_kind": "report"', out)
        self.assertIn('"table": true', out)

    def test_doctor_passes(self):
        code, out, err = run_cli(["doctor"])
        self.assertEqual(code, 0, err)
        self.assertIn("模板自检", out)
        self.assertIn("mmdc", out)

    def test_frontmatter_kind_beats_doc_spec(self):
        spec = self.tmp / "force-report.doc.yml"
        spec.write_text("kind: report\n", encoding="utf-8")
        code, _, err = self.build("novel.md", "--doc", str(spec))
        self.assertEqual(code, 0, err)
        text = (self.tmp / "novel.typ").read_text(encoding="utf-8")
        self.assertIn("chapter-prefix: true", text)

    def test_dropcap_skips_paragraph_with_markup(self):
        md = self.tmp / "novel2.md"
        md.write_text(
            "---\nkind: novel\ntitle: 测试\nauthor: 张三\n---\n\n"
            "# 初见\n\n**加粗**开头会让首字下沉退让。\n\n第二段普通文字。\n",
            encoding="utf-8",
        )
        out = self.tmp / "novel2.pdf"
        code, _, err = run_cli(["build", str(md), "-o", str(out), "--check", "none"])
        self.assertEqual(code, 0, err)
        text = out.with_suffix(".typ").read_text(encoding="utf-8")
        self.assertNotIn('#dropcap("', text)
        self.assertIn("#strong[", text)


    def test_image_outside_the_output_directory_still_builds(self):
        images = self.tmp / "images"
        images.mkdir()
        (images / "fig.png").write_bytes(PNG_1PX)
        out_dir = self.tmp / "out"
        out_dir.mkdir()
        md = self.tmp / "img.md"
        md.write_text("---\ntitle: 测试\n---\n\n![渠道效率](images/fig.png)\n", encoding="utf-8")
        code, _, err = run_cli(["build", str(md), "-o", str(out_dir / "img.pdf"),
                                "--check", "none"])
        self.assertEqual(code, 0, err)
        typ = (out_dir / "img.typ").read_text(encoding="utf-8")
        self.assertIn("pdfgen-root:", typ)
        self.assertIn('image("/', typ)


class DialectTests(unittest.TestCase):
    """The pinned pandoc dialect is a contract: these guard it (ADR-0003)."""

    REQUIRED = (
        "+citations",
        "+implicit_figures",
        "+fenced_code_attributes",
        "+bracketed_spans",
        "+fenced_divs",
        "+lists_without_preceding_blankline",
    )
    FORBIDDEN = ("-smart", "-raw_tex", "-latex_macros")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix=".pdfgen-test-", dir=str(ROOT)))
        (self.tmp / "refs.bib").write_text(BIB, encoding="utf-8")
        (self.tmp / "a.png").write_bytes(PNG_1PX)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @unittest.skipUnless(shutil.which("pandoc"), "需要 pandoc")
    def test_constant_pins_the_decided_extensions(self):
        for ext in self.REQUIRED:
            self.assertIn(ext, bp.FROM_FORMAT)
        for ext in self.FORBIDDEN:
            self.assertIn(ext, bp.FROM_FORMAT)
        self.assertTrue(bp.FROM_FORMAT.startswith("markdown"))

    @unittest.skipUnless(HAVE_DEPS, "需要 typst 与 pandoc")
    def test_dialect_parses_citations_attributes_and_lists(self):
        md = self.tmp / "doc.md"
        md.write_text(
            "---\ntitle: 测试\nbibliography: refs.bib\n---\n\n"
            "这是一段足够长的中文正文，用来让语言检测判定为中文而不是英文。\n\n"
            "![渠道效率](a.png){#fig:channels width=70%}\n\n"
            "他说：\n- 一\n- 二\n\n正文 [@doe2020]。\n",
            encoding="utf-8",
        )
        code, _, err = run_cli(["build", str(md), "-o", str(self.tmp / "doc.pdf"),
                                "--check", "none"])
        self.assertEqual(code, 0, err)
        typ = (self.tmp / "doc.typ").read_text(encoding="utf-8")
        self.assertIn("@doe2020", typ)
        self.assertIn("#figure(", typ)
        self.assertIn("width: 70.0%", typ)
        self.assertIn("- 一", typ)

    def test_bad_from_format_explains_itself(self):
        code, _, err = run_cli(["build", str(ROOT / "examples/note.md"),
                                "--from", "bogus", "--check", "none"])
        self.assertEqual(code, 1)
        self.assertIn("不认识的格式", err)


BIB = """
@book{doe2020,
  author = {Doe, John},
  title = {A Book Title},
  year = {2020},
  publisher = {Acme Press},
}
"""


@unittest.skipUnless(HAVE_DEPS, "需要 typst 与 pandoc")
class CitationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix=".pdfgen-test-", dir=str(ROOT)))
        (self.tmp / "refs.bib").write_text(BIB, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build_doc(self, source: str, *extra: str):
        md = self.tmp / "doc.md"
        md.write_text(source, encoding="utf-8")
        return run_cli(["build", str(md), "-o", str(self.tmp / "doc.pdf"),
                        "--check", "none", *extra])

    def test_bibliography_renders_chinese_citations(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\nbibliography: refs.bib\n---\n\n"
            "这是一段足够长的中文正文，用来让语言检测判定为中文而不是英文。\n\n"
            "正文 [@doe2020]。\n"
        )
        self.assertEqual(code, 0, err)
        typ = (self.tmp / "doc.typ").read_text(encoding="utf-8")
        self.assertIn('has-path: "yes"', typ)
        self.assertIn('path: "refs.bib"', typ)
        self.assertIn('style: "gb-7714-2015-numeric"', typ)
        self.assertIn('title: "参考文献"', typ)
        self.assertIn("@doe2020", typ)
        self.assertGreater(bp.page_count(self.tmp / "doc.typ"), 0)

    def test_english_document_defaults_to_ieee(self):
        code, _, err = self.build_doc(
            "---\ntitle: Report\nbibliography: refs.bib\n---\n\n"
            "This paragraph is long enough to be detected as English prose. [@doe2020]\n"
        )
        self.assertEqual(code, 0, err)
        typ = (self.tmp / "doc.typ").read_text(encoding="utf-8")
        self.assertIn('style: "ieee"', typ)
        self.assertIn('title: "References"', typ)

    def test_article_defaults_to_apa(self):
        code, _, err = self.build_doc(
            "---\nkind: article\ntitle: Report\nbibliography: refs.bib\n---\n\n"
            "This paragraph is long enough to be detected as English prose. [@doe2020]\n"
        )
        self.assertEqual(code, 0, err)
        typ = (self.tmp / "doc.typ").read_text(encoding="utf-8")
        self.assertIn('style: "apa"', typ)

    def test_locator_short_form_survives(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\nbibliography: refs.bib\n---\n\n"
            "这是一段足够长的中文正文，用来让语言检测判定为中文而不是英文。\n\n"
            "正文 [@doe2020, p. 33]。\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("@doe2020[p. 33]", (self.tmp / "doc.typ").read_text(encoding="utf-8"))

    def test_csl_file_style_is_resolved(self):
        shutil.copy(ROOT / "test" / "fixtures" / "minimal.csl", self.tmp / "minimal.csl")
        code, _, err = self.build_doc(
            "---\ntitle: 测试\nbibliography: refs.bib\n---\n\n"
            "这是一段足够长的中文正文，用来让语言检测判定为中文而不是英文。\n\n"
            "正文 [@doe2020]。\n",
            "--set", "cite.style=minimal.csl",
        )
        self.assertEqual(code, 0, err)
        self.assertIn('style: "minimal.csl"', (self.tmp / "doc.typ").read_text(encoding="utf-8"))

    def test_absolute_csl_path_is_rewritten_for_typst(self):
        csl = self.tmp / "minimal.csl"
        shutil.copy(ROOT / "test" / "fixtures" / "minimal.csl", csl)
        code, _, err = self.build_doc(
            "---\ntitle: 测试\nbibliography: refs.bib\n---\n\n"
            "这是一段足够长的中文正文，用来让语言检测判定为中文而不是英文。\n\n"
            "正文 [@doe2020]。\n",
            "--set", f"cite.style={csl}",
        )
        self.assertEqual(code, 0, err)
        typ = (self.tmp / "doc.typ").read_text(encoding="utf-8")
        self.assertIn('style: "minimal.csl"', typ)
        self.assertNotIn(str(csl), typ)

    def test_missing_bibliography_file_fails(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\nbibliography: nope.bib\n---\n\n正文。\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("nope.bib", err)

    def test_unknown_citation_key_fails(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\nbibliography: refs.bib\n---\n\n正文 [@smith2021]。\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("smith2021", err)


PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@unittest.skipUnless(HAVE_DEPS, "需要 typst 与 pandoc")
class CrossReferenceTests(unittest.TestCase):
    """`@fig:` / `@tab:` / `@eq:` / `@sec:` are refs; every other @id is a citation."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix=".pdfgen-test-", dir=str(ROOT)))
        (self.tmp / "a.png").write_bytes(PNG_1PX)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build_doc(self, body: str, *extra: str):
        md = self.tmp / "doc.md"
        md.write_text(body, encoding="utf-8")
        return run_cli(["build", str(md), "-o", str(self.tmp / "doc.pdf"),
                        "--check", "none", *extra])

    def typ(self) -> str:
        return (self.tmp / "doc.typ").read_text(encoding="utf-8")

    def test_figure_reference_becomes_typst_ref(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            "![渠道效率](a.png){#fig:channels width=60%}\n\n见图 @fig:channels。\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("#ref(<fig:channels>)", self.typ())

    def test_table_and_section_references(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            "# 方法 {#sec:method}\n\n"
            ": 槽位表 {#tab:slots}\n\n| a | b |\n|---|---|\n\n"
            "见表 @tab:slots 与 @sec:method。\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("#ref(<tab:slots>)", self.typ())
        self.assertIn("#ref(<sec:method>)", self.typ())

    def test_equation_reference_needs_numbering(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n$$ y = mx + b \\label{eq:line} $$\n\n见 @eq:line。\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("math.numbering", err)

    def test_equation_reference_works_with_numbering(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n$$ y = mx + b \\label{eq:line} $$\n\n见 @eq:line。\n",
            "--set", "math.numbering=(1)",
        )
        self.assertEqual(code, 0, err)
        self.assertIn("#ref(<eq:line>)", self.typ())

    def test_bracketed_reference_also_converts(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            "![渠道效率](a.png){#fig:channels width=60%}\n\n见图 [@fig:channels]。\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("#ref(<fig:channels>)", self.typ())

    def test_citation_is_not_a_reference(self):
        (self.tmp / "refs.bib").write_text(
            "@book{doe2020, author={Doe, John}, title={T}, year={2020}, publisher={P}}\n",
            encoding="utf-8",
        )
        code, _, err = self.build_doc(
            "---\ntitle: 测试\nbibliography: refs.bib\n---\n\n"
            "这是一段足够长的中文正文，用来让语言检测判定为中文而不是英文。\n\n"
            "正文 [@doe2020]。\n"
        )
        self.assertEqual(code, 0, err)
        typ = self.typ()
        self.assertNotIn("#ref(<doe2020>)", typ)
        self.assertIn("@doe2020", typ)

    def test_unknown_reference_names_the_id(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n见图 @fig:nope。\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("fig:nope", err)


@unittest.skipUnless(HAVE_DEPS, "需要 typst 与 pandoc")
class SidenoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix=".pdfgen-test-", dir=str(ROOT)))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build_doc(self, body: str, *extra: str):
        md = self.tmp / "doc.md"
        md.write_text(body, encoding="utf-8")
        return run_cli(["build", str(md), "-o", str(self.tmp / "doc.pdf"),
                        "--check", "none", *extra])

    def typ(self) -> str:
        return (self.tmp / "doc.typ").read_text(encoding="utf-8")

    def test_inline_sidenote_reaches_the_template(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n正文一段[边注内容]{.sidenote}，后面继续。\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("#sidenote[", self.typ())

    def test_block_sidenote_reaches_the_template(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n::: {.sidenote}\n块级边注内容。\n:::\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("#sidenote-block[", self.typ())

    def test_markers_switch_the_document_into_margin_mode(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n正文[边注]{.sidenote}。\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn('style: "margin"', self.typ())

    def test_margin_style_knob_reaches_the_style_dict(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n正文[边注]{.sidenote}。\n",
            "--set", "note.width=3.5cm", "--set", "note.gap=8pt",
        )
        self.assertEqual(code, 0, err)
        typ = self.typ()
        self.assertIn("width: 3.5cm", typ)
        self.assertIn("gap: 8pt", typ)

    def test_default_document_without_markers_stays_footnote(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n正文[^1]。\n\n[^1]: 页脚注释。\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn('style: "footnote"', self.typ())

    def test_explicit_footnote_choice_keeps_the_footer(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n正文[边注]{.sidenote}。\n",
            "--set", "note.style=footnote",
        )
        self.assertEqual(code, 0, err)
        self.assertIn('style: "footnote"', self.typ())

    def test_code_example_does_not_switch_margin_mode(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            "示例：\n\n```markdown\n正文[注]{.sidenote}。\n```\n\n正文。\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn('style: "footnote"', self.typ())

    def test_long_sidenote_warns(self):
        long_note = "这是一条很长的边注，" * 30
        code, out, err = self.build_doc(
            f"---\ntitle: 测试\n---\n\n正文[{long_note}]{{.sidenote}}。\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("边注过长", out + err)

    def test_close_sidenotes_warn(self):
        code, out, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            "正文[注一]{.sidenote}。\n\n正文[注二]{.sidenote}。\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("间距过近", out + err)

    def test_style_subcommand_resolves_the_same_note_mode(self):
        self.build_doc("---\ntitle: 测试\n---\n\n正文[边注]{.sidenote}。\n")
        code, out, err = run_cli(["style", str(self.tmp / "doc.md")])
        self.assertEqual(code, 0, err)
        self.assertIn("style: margin", out)

    def test_footnote_inside_a_semantic_block_moves_to_the_margin(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            "::: {.notice}\n正文[^1]。\n\n[^1]: 块内脚注。\n:::\n",
            "--set", "note.style=margin",
        )
        self.assertEqual(code, 0, err)
        self.assertIn("#sidenote[", self.typ())


@unittest.skipUnless(HAVE_DEPS, "需要 typst 与 pandoc")
class CodeLineNumberTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix=".pdfgen-test-", dir=str(ROOT)))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build_doc(self, body: str, *extra: str):
        md = self.tmp / "doc.md"
        md.write_text(body, encoding="utf-8")
        return run_cli(["build", str(md), "-o", str(self.tmp / "doc.pdf"),
                        "--check", "none", *extra])

    def typ(self) -> str:
        return (self.tmp / "doc.typ").read_text(encoding="utf-8")

    def test_line_numbers_are_off_by_default(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n```python\na = 1\n```\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("line-numbers: false", self.typ())
        self.assertNotIn("#numbered-code[", self.typ())

    def test_knob_turns_on_every_code_block(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            "```python\na = 1\n```\n\n```python\nb = 2\n```\n",
            "--set", "code.line-numbers=true",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(self.typ().count("#numbered-code["), 2)

    def test_single_block_opts_in(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n```python {.line-numbers}\na = 1\n```\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("#numbered-code[", self.typ())

    def test_single_block_opts_out(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            "```python {.no-line-numbers}\na = 1\n```\n",
            "--set", "code.line-numbers=true",
        )
        self.assertEqual(code, 0, err)
        self.assertNotIn("#numbered-code[", self.typ())

    def test_inline_code_is_not_numbered(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n行内 `print(1)` 代码。\n\n```python\na = 1\n```\n",
            "--set", "code.line-numbers=true",
        )
        self.assertEqual(code, 0, err)
        # Only the block is wrapped; inline code carries no wrapper and, because
        # the show rule is scoped to the wrapper, cannot be numbered.
        self.assertEqual(self.typ().count("#numbered-code["), 1)

    def test_code_with_fence_material_still_builds(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            "```python {.line-numbers}\n"
            "line = '``` and ] 和尾随空格   '\n"
            "other = [1, 2]\n"
            "```\n",
            "--set", "code.line-numbers=true",
        )
        self.assertEqual(code, 0, err)
        self.assertIn("和尾随空格", self.typ())

    def test_marker_class_never_becomes_the_language_tag(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n```{.line-numbers}\na = 1\n```\n"
        )
        self.assertEqual(code, 0, err)
        typ = self.typ()
        self.assertIn("#numbered-code[", typ)
        self.assertNotIn("line-numbers", typ.split("#show: doc.with")[-1])

    def test_opt_out_class_is_stripped_in_a_plain_build(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n```{.no-line-numbers}\na = 1\n```\n"
        )
        self.assertEqual(code, 0, err)
        self.assertNotIn("no-line-numbers", self.typ().split("#show: doc.with")[-1])

    def test_code_inside_a_semantic_block_is_numbered(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n::: {.notice}\n```python\na = 1\n```\n:::\n",
            "--set", "code.line-numbers=true",
        )
        self.assertEqual(code, 0, err)
        typ = self.typ()
        # Wrapping must happen before the Div is flattened, i.e. inside #notice.
        self.assertLess(typ.index("#notice["), typ.index("#numbered-code["))


DOT_DIAGRAM = "digraph G {\n  rankdir=LR;\n  A -> B;\n}\n"


@unittest.skipUnless(HAVE_DEPS, "需要 typst 与 pandoc")
class DiagramTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix=".pdfgen-test-", dir=str(ROOT)))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build_doc(self, body: str, *extra: str):
        md = self.tmp / "doc.md"
        md.write_text(body, encoding="utf-8")
        return run_cli(["build", str(md), "-o", str(self.tmp / "doc.pdf"),
                        "--check", "none", *extra])

    def typ(self) -> str:
        return (self.tmp / "doc.typ").read_text(encoding="utf-8")

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_dot_fence_becomes_a_captioned_figure(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            f'```dot {{caption="数据流" width=60%}}\n{DOT_DIAGRAM}```\n'
        )
        self.assertEqual(code, 0, err)
        typ = self.typ()
        self.assertIn("#figure(image(", typ)
        self.assertIn('caption: [#text("数据流")]', typ)
        self.assertIn("width: 60%", typ)
        self.assertTrue(list((self.tmp / ".pdfgen" / "diagrams").glob("*.svg")))

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_diagram_label_becomes_a_figure_label(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            f"```dot {{#fig:flow}}\n{DOT_DIAGRAM}```\n\n见图 @fig:flow。\n"
        )
        self.assertEqual(code, 0, err)
        typ = self.typ()
        self.assertIn("<fig:flow>", typ)
        self.assertIn("#ref(<fig:flow>)", typ)

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_rendered_svg_is_cached_between_builds(self):
        body = f"---\ntitle: 测试\n---\n\n```dot\n{DOT_DIAGRAM}```\n"
        self.assertEqual(self.build_doc(body)[0], 0)
        svg = next((self.tmp / ".pdfgen" / "diagrams").glob("*.svg"))
        stamp = svg.stat().st_mtime_ns
        self.assertEqual(self.build_doc(body)[0], 0)
        self.assertEqual(svg.stat().st_mtime_ns, stamp)

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_broken_diagram_fails_with_a_pointer(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n```dot\ndigraph { -> }\n```\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("渲染失败", err)
        self.assertIn("doc.md:", err)

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_diagram_nested_in_a_list_is_still_found(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            '- 列表项：\n\n  ```dot {caption="列表里的图"}\n  digraph { A -> B; }\n  ```\n'
        )
        self.assertEqual(code, 0, err)
        self.assertIn('caption: [#text("列表里的图")]', self.typ())

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_escaped_quotes_in_caption_survive(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            '```dot {caption="他说 \\"你好\\" 完了"}\n'
            f"{DOT_DIAGRAM}```\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn('caption: [#text("他说 \\"你好\\" 完了")]', self.typ())

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_indented_sample_does_not_shift_the_index(self):
        sample = "    ```dot\n    digraph { A -> B; }\n    ```\n"
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            + sample
            + '\n```dot {caption="真图"}\ndigraph { C -> D; }\n```\n'
        )
        self.assertEqual(code, 0, err)
        typ = self.typ()
        self.assertIn('caption: [#text("真图")]', typ)
        self.assertEqual(typ.count("#figure(image("), 1)

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_two_identical_diagrams_with_different_labels_stay_distinct(self):
        body = (
            "---\ntitle: 测试\n---\n\n"
            f"```dot {{#fig:a}}\n{DOT_DIAGRAM}```\n\n"
            f"```dot {{#fig:b}}\n{DOT_DIAGRAM}```\n"
        )
        code, _, err = self.build_doc(body)
        self.assertEqual(code, 0, err)
        typ = self.typ()
        self.assertIn("<fig:a>", typ)
        self.assertIn("<fig:b>", typ)

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_a_code_sample_of_dot_source_is_not_converted(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            f"```text\n{DOT_DIAGRAM}```\n"
        )
        self.assertEqual(code, 0, err)
        self.assertNotIn("#figure(image(", self.typ())

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_tilde_fences_are_recognised(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            f'~~~dot {{caption="波浪围栏"}}\n{DOT_DIAGRAM}~~~\n'
        )
        self.assertEqual(code, 0, err)
        self.assertIn('caption: [#text("波浪围栏")]', self.typ())

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_unknown_diagram_option_fails(self):
        code, _, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            f"```dot {{widht=60%}}\n{DOT_DIAGRAM}```\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("widht", err)
        self.assertIn("caption", err)

    def test_mermaid_renders_through_a_windows_cmd_shim(self):
        shim_dir = self.tmp / "bin"
        shim_dir.mkdir()
        script = self.tmp / "fake_mmdc.py"
        script.write_text(
            "import pathlib, sys\n"
            "args = sys.argv[1:]\n"
            "out = args[args.index('-o') + 1]\n"
            "pathlib.Path(out).write_text(\n"
            "    '<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\">'\n"
            "    '</svg>', encoding='utf-8')\n",
            encoding="utf-8",
        )
        (shim_dir / "mmdc.cmd").write_text(
            f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8"
        )
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(shim_dir) + os.pathsep + old_path
        try:
            code, _, err = self.build_doc(
                "---\ntitle: 测试\n---\n\n```mermaid\ngraph TD; A-->B\n```\n"
            )
        finally:
            os.environ["PATH"] = old_path
        self.assertEqual(code, 0, err)
        self.assertIn("#figure(image(", self.typ())

    @unittest.skipUnless(not shutil.which("mmdc"), "本机装了 mmdc 就测不到降级")
    def test_degraded_diagram_keeps_caption_and_label(self):
        code, out, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n"
            '```mermaid {#fig:flow caption="Mermaid 示例"}\n'
            "graph TD; A-->B;\n```\n\n见 @fig:flow。\n"
        )
        self.assertEqual(code, 0, err)
        typ = self.typ()
        self.assertIn('caption: [#text("Mermaid 示例")]', typ)
        self.assertIn("<fig:flow>", typ)
        self.assertIn("#ref(<fig:flow>)", typ)

    @unittest.skipUnless(not shutil.which("mmdc"), "本机装了 mmdc 就测不到降级")
    def test_mermaid_without_renderer_falls_back_to_source(self):
        code, out, err = self.build_doc(
            "---\ntitle: 测试\n---\n\n```mermaid\ngraph TD; A-->B\n```\n"
        )
        self.assertEqual(code, 0, err)
        self.assertIn("mmdc", out + err)
        self.assertIn("```mermaid", self.typ())


if __name__ == "__main__":
    unittest.main()


