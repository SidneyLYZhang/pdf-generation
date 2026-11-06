"""End-to-end CLI tests: build real documents.

Skipped automatically when typst or pandoc is missing.
"""

from __future__ import annotations

import contextlib
import io
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


if __name__ == "__main__":
    unittest.main()
