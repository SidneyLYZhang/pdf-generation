"""The generated reference tables must match the code.

`references/style-knobs.md` and the two generated regions inside
`references/typography.md` are written by `scripts/gen_style_docs.py`; these
tests are the gate that stops either from drifting away from `build_pdf.py`.
"""

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_pdf as bp  # noqa: E402
import gen_style_docs as gd  # noqa: E402


def quiet(argv: list[str]) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return gd.main(argv)


class GeneratedDocsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix=".pdfgen-test-docs-", dir=str(ROOT)))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_style_knobs_doc_is_up_to_date(self):
        disk = gd.STYLE_KNOBS.read_text(encoding="utf-8")
        self.assertEqual(
            gd.render_style_knobs(), disk,
            "references/style-knobs.md 过期：跑 python scripts/gen_style_docs.py",
        )

    def test_typography_tables_are_up_to_date(self):
        disk = gd.TYPOGRAPHY.read_text(encoding="utf-8")
        self.assertEqual(
            gd.render_typography(disk), disk,
            "references/typography.md 生成的表过期：跑 python scripts/gen_style_docs.py",
        )

    def test_rule_summary_covers_every_rule(self):
        self.assertEqual(set(bp.RULE_SUMMARY), set(bp.RULE_SEVERITY))

    def test_typography_doc_carries_every_generated_marker(self):
        disk = gd.TYPOGRAPHY.read_text(encoding="utf-8")
        for marker in (gd.RULES_BEGIN, gd.RULES_END, gd.METRICS_BEGIN, gd.METRICS_END):
            self.assertIn(marker, disk)

    def test_check_mode_is_clean_on_this_repo(self):
        self.assertEqual(quiet(["--check"]), 0)

    def test_check_mode_fails_and_write_repairs_a_stale_knob_doc(self):
        stale = self.tmp / "style-knobs.md"
        stale.write_text("旧的\n", encoding="utf-8")
        with mock.patch.object(gd, "STYLE_KNOBS", stale):
            self.assertEqual(quiet(["--check"]), 1)
            # Not a check run: the same call repairs the file instead.
            self.assertEqual(quiet([]), 0)
        self.assertEqual(stale.read_text(encoding="utf-8"), gd.render_style_knobs())

    def test_check_mode_fails_on_a_stale_rule_table(self):
        stale = self.tmp / "typography.md"
        stale.write_text(
            f"{gd.RULES_BEGIN}\n| 旧表 |\n{gd.RULES_END}\n"
            f"{gd.METRICS_BEGIN}\n{gd.METRICS_END}\n",
            encoding="utf-8",
        )
        with mock.patch.object(gd, "TYPOGRAPHY", stale):
            self.assertEqual(quiet(["--check"]), 1)

    def test_missing_typography_doc_is_reported_not_crashed(self):
        with mock.patch.object(gd, "TYPOGRAPHY", self.tmp / "nope.md"):
            self.assertEqual(quiet(["--check"]), 1)

    def test_missing_markers_are_reported_with_the_fix(self):
        with self.assertRaises(ValueError) as caught:
            gd.render_typography("没有标记的文档")
        self.assertIn("标记", str(caught.exception))


class EntryDocTests(unittest.TestCase):
    """The entry has to carry the gate's numbers, not just point at them."""

    def entry(self) -> str:
        return (ROOT / "SKILL.md").read_text(encoding="utf-8")

    def test_entry_quotes_the_ranges_the_code_uses(self):
        entry = self.entry()
        low, high = bp.CHINESE_LEADING
        self.assertIn(f"中文行距 {low:.2f}–{high:.2f}×", entry)
        low, high = bp.CHINESE_MEASURE
        other_low, other_high = bp.WESTERN_MEASURE
        self.assertIn(f"中文 {low}–{high}、西文 {other_low}–{other_high}", entry)
        self.assertIn(f"一级标题 ≥ 正文 {bp.HEADING_RATIO_MIN:g} 倍", entry)
        self.assertIn(f"标题层级 ≤ {bp.MAX_HEADING_LEVEL} 级", entry)

    def test_every_reference_doc_is_reachable_from_the_entry(self):
        entry = self.entry()
        for path in sorted((ROOT / "references").glob("*.md")):
            self.assertIn(path.name, entry, f"SKILL.md 没有指向 {path.name}")

    def test_entry_links_the_glossary(self):
        self.assertIn("CONTEXT.md", self.entry())

    def test_install_contract_ships_what_the_entry_links(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("CONTEXT.md", install, "安装契约漏了 CONTEXT.md，装好后入口会断链")

    def test_glossary_defines_the_new_terms(self):
        glossary = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")
        for term in ("**Scene**", "**Layout plan**", "**Principle check**", "**Deviation**"):
            self.assertIn(term, glossary)

    def test_raw_principle_docs_point_at_the_spec(self):
        for name in ("总排版原则.md", "细节排版原则.md"):
            text = (ROOT / "docs" / name).read_text(encoding="utf-8")
            # The full relative path matters: docs/ needs the ../ hop.
            self.assertIn("../references/typography.md", text, name)

    def test_entry_keeps_the_six_steps_and_the_four_line_plan(self):
        entry = self.entry()
        for number in range(1, 7):
            self.assertIn(f"## {number}.", entry)
        for row in ("| 方案 |", "| 依据 |", "| 自检 |", "| 偏离 |"):
            self.assertIn(row, entry)


if __name__ == "__main__":
    unittest.main()
