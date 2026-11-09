"""Unit tests for style parsing and resolution (no typst/pandoc needed)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_pdf as bp  # noqa: E402


class YamlSubsetTests(unittest.TestCase):
    def test_nested_map_and_list(self):
        data = bp.parse_simple_yaml(
            "kind: note\n"
            "style:\n"
            "  page:\n"
            "    margin: 2cm\n"
            "  text:\n"
            "    font:\n"
            "      - Noto Serif SC\n"
            "      - Libertinus Serif\n"
        )
        self.assertEqual(data["kind"], "note")
        self.assertEqual(data["style"]["page"]["margin"], "2cm")
        self.assertEqual(data["style"]["text"]["font"], ["Noto Serif SC", "Libertinus Serif"])

    def test_comments_bools_numbers(self):
        data = bp.parse_simple_yaml(
            "a: 1  # trailing comment\nb: true\nc: 2.5\nd: \"a # b\"\n"
        )
        self.assertEqual(data["a"], 1)
        self.assertIs(data["b"], True)
        self.assertEqual(data["c"], 2.5)
        self.assertEqual(data["d"], "a # b")

    def test_double_quoted_escapes(self):
        data = bp.parse_simple_yaml('line: "示例公司\\n示例路 88 号"\n')
        self.assertEqual(data["line"], "示例公司\n示例路 88 号")

    def test_block_scalar(self):
        data = bp.parse_simple_yaml("abstract: |\n  第一段\n\n  第二段\nnext: 1\n")
        self.assertIn("第一段", data["abstract"])
        self.assertIn("第二段", data["abstract"])
        self.assertEqual(data["next"], 1)

    def test_tabs_rejected(self):
        with self.assertRaises(bp.SpecError):
            bp.parse_simple_yaml("a:\n\tb: 1\n")


class ResolveStyleTests(unittest.TestCase):
    def test_kind_preset_beats_default(self):
        style = bp.resolve_style("book", {}, [], "zh")
        self.assertEqual(style["page"]["paper"], "6x9")
        self.assertEqual(style["text"]["first-line-indent"], "2em")

    def test_doc_spec_beats_preset(self):
        style = bp.resolve_style("book", {"style": {"page": {"paper": "a4"}}}, [], "zh")
        self.assertEqual(style["page"]["paper"], "a4")

    def test_set_beats_everything(self):
        style = bp.resolve_style(
            "book", {"style": {"page": {"margin": "1cm"}}}, ["page.margin=3cm"], "zh"
        )
        self.assertEqual(style["page"]["margin"], "3cm")

    def test_flat_top_level_style_shape(self):
        style = bp.resolve_style("report", {"page": {"margin": "1.5cm"}}, [], "zh")
        self.assertEqual(style["page"]["margin"], "1.5cm")

    def test_palette_colours_resolved(self):
        style = bp.resolve_style("report", {}, ["color.palette=indigo"], "zh")
        self.assertTrue(style["color"]["accent"].startswith("#"))
        self.assertEqual(style["color"]["accent"], bp.PALETTES["indigo"]["accent"])

    def test_unknown_nested_knob_rejected(self):
        with self.assertRaises(bp.SpecError):
            bp.resolve_style("report", {"style": {"page": {"margins": "2cm"}}}, [], "zh")

    def test_font_list_json_syntax(self):
        style = bp.resolve_style("report", {}, ['text.font=["A", "B"]'], "zh")
        self.assertEqual(style["text"]["font"], ["A", "B"])

    def test_unknown_knob_rejected(self):
        with self.assertRaises(bp.SpecError):
            bp.resolve_style("report", {}, ["page.margins=2cm"], "zh")

    def test_removed_letter_knobs_rejected(self):
        with self.assertRaises(bp.SpecError):
            bp.resolve_style("letter", {}, ["letter.sender=x"], "zh")

    def test_bad_length_rejected(self):
        with self.assertRaises(bp.SpecError):
            bp.resolve_style("report", {}, ["text.size=huge"], "zh")

    def test_toc_depth_range(self):
        with self.assertRaises(bp.SpecError):
            bp.resolve_style("report", {}, ["toc.depth=0"], "zh")
        self.assertEqual(bp.resolve_style("report", {}, ["toc.depth=3"], "zh")["toc"]["depth"], 3)

    def test_numbering_rejects_unsupported_pattern(self):
        with self.assertRaises(bp.SpecError):
            bp.resolve_style("report", {}, ["heading.numbering=第1章"], "zh")

    def test_page_number_format_validated(self):
        with self.assertRaises(bp.SpecError):
            bp.resolve_style("report", {}, ["furniture.page-number-format=第页"], "zh")

    def test_zero_paragraph_spacing_raised(self):
        style = bp.resolve_style("book", {}, ["text.paragraph-spacing=0em"], "zh")
        self.assertEqual(style["text"]["paragraph-spacing"], "4.5pt")

    def test_small_paragraph_spacing_raised_and_noted(self):
        notes = []
        style = bp.resolve_style("book", {}, ["text.paragraph-spacing=2pt"], "zh", notes)
        self.assertEqual(style["text"]["paragraph-spacing"], "4.5pt")
        self.assertEqual(len(notes), 1)

    def test_safe_paragraph_spacing_kept(self):
        style = bp.resolve_style("report", {}, [], "zh")
        self.assertEqual(style["text"]["paragraph-spacing"], "1em")

    def test_language_picks_font_stack(self):
        zh = bp.resolve_style("report", {}, [], "zh")
        en = bp.resolve_style("report", {}, [], "en")
        self.assertIn("Noto Serif SC", zh["text"]["font"])
        self.assertEqual(en["text"]["font"], ["Libertinus Serif"])


class CitationStyleTests(unittest.TestCase):
    def test_style_defaults_follow_language_and_kind(self):
        self.assertEqual(bp.resolve_style("report", {}, [], "zh")["cite"]["style"],
                         "gb-7714-2015-numeric")
        self.assertEqual(bp.resolve_style("report", {}, [], "en")["cite"]["style"], "ieee")
        self.assertEqual(bp.resolve_style("article", {}, [], "en")["cite"]["style"], "apa")
        self.assertEqual(bp.resolve_style("article", {}, [], "zh")["cite"]["style"], "apa")

    def test_title_defaults_follow_language(self):
        self.assertEqual(bp.resolve_style("report", {}, [], "zh")["cite"]["title"], "参考文献")
        self.assertEqual(bp.resolve_style("report", {}, [], "en")["cite"]["title"], "References")

    def test_enabled_follows_bibliography_presence(self):
        self.assertFalse(bp.resolve_style("report", {}, [], "zh")["cite"]["enabled"])
        self.assertTrue(
            bp.resolve_style("report", {}, [], "zh", has_bibliography=True)["cite"]["enabled"]
        )
        self.assertTrue(bp.resolve_style("report", {}, ["cite.enabled=true"], "zh")["cite"]["enabled"])

    def test_style_can_be_overridden(self):
        style = bp.resolve_style("report", {}, ["cite.style=apa", "cite.title=文献"], "zh")
        self.assertEqual(style["cite"]["style"], "apa")
        self.assertEqual(style["cite"]["title"], "文献")

    def test_explicit_text_lang_moves_the_citation_defaults(self):
        style = bp.resolve_style("report", {}, ["text.lang=en"], "zh")
        self.assertEqual(style["cite"]["style"], "ieee")
        self.assertEqual(style["cite"]["title"], "References")


class SidenoteStyleTests(unittest.TestCase):
    def test_default_is_footnote_and_textbook_is_margin(self):
        self.assertEqual(bp.resolve_style("report", {}, [], "zh")["note"]["style"], "footnote")
        self.assertEqual(bp.resolve_style("textbook", {}, [], "zh")["note"]["style"], "margin")

    def test_explicit_markers_force_margin_space(self):
        style = bp.resolve_style("report", {}, [], "zh", has_sidenotes=True)
        self.assertEqual(style["note"]["style"], "margin")

    def test_explicit_footnote_choice_wins_over_markers(self):
        style = bp.resolve_style("report", {}, ["note.style=footnote"], "zh", has_sidenotes=True)
        self.assertEqual(style["note"]["style"], "footnote")

    def test_bad_note_style_rejected(self):
        with self.assertRaises(bp.SpecError):
            bp.resolve_style("report", {}, ["note.style=left"], "zh")

    def test_note_knobs_flow_through(self):
        style = bp.resolve_style(
            "report", {}, ["note.width=3cm", "note.gap=6pt", "note.size=7pt"], "zh"
        )
        self.assertEqual(style["note"]["width"], "3cm")
        self.assertEqual(style["note"]["gap"], "6pt")
        self.assertEqual(style["note"]["size"], "7pt")


class CodeStyleTests(unittest.TestCase):
    def test_line_numbers_default_off_and_can_be_turned_on(self):
        self.assertFalse(bp.resolve_style("report", {}, [], "zh")["code"]["line-numbers"])
        self.assertTrue(
            bp.resolve_style("report", {}, ["code.line-numbers=true"], "zh")["code"]["line-numbers"]
        )


class SidenoteScanTests(unittest.TestCase):
    def test_no_notes(self):
        self.assertEqual(bp.inspect_sidenotes("普通正文。"), (False, [], 0))

    def test_inline_note_is_found(self):
        present, overlong, crowded = bp.inspect_sidenotes("正文[注]{.sidenote}。")
        self.assertTrue(present)
        self.assertEqual(overlong, [])
        self.assertEqual(crowded, 0)

    def test_block_note_is_found(self):
        present, _, _ = bp.inspect_sidenotes("::: {.sidenote}\n块级注。\n:::\n")
        self.assertTrue(present)

    def test_fenced_code_is_ignored(self):
        text = "示例：\n\n```markdown\n正文[注]{.sidenote}。\n```\n\n正文。\n"
        self.assertEqual(bp.inspect_sidenotes(text), (False, [], 0))

    def test_long_note_is_reported(self):
        present, overlong, _ = bp.inspect_sidenotes("正文[" + "很长的注" * 80 + "]{.sidenote}。")
        self.assertTrue(present)
        self.assertEqual(len(overlong), 1)
        self.assertGreater(overlong[0], bp.LONG_NOTE_CHARS)

    def test_close_notes_are_counted(self):
        text = "正文[注一]{.sidenote}。\n\n正文[注二]{.sidenote}。\n"
        _, _, crowded = bp.inspect_sidenotes(text)
        self.assertEqual(crowded, 1)

    def test_a_long_first_note_does_not_hide_a_close_pair(self):
        long_note = "很长的注" * 60
        text = f"正文[{long_note}]{{.sidenote}}。\n\n正文[注二]{{.sidenote}}。\n"
        _, _, crowded = bp.inspect_sidenotes(text)
        self.assertEqual(crowded, 1)

    def test_pagebreak_separates_notes(self):
        text = (
            "正文[注一]{.sidenote}。\n\n::: pagebreak\n:::\n\n正文[注二]{.sidenote}。\n"
        )
        _, _, crowded = bp.inspect_sidenotes(text)
        self.assertEqual(crowded, 0)

    def test_footnotes_are_scanned_only_in_margin_mode(self):
        text = "正文[^1]。\n\n[^1]: " + "很长的脚注" * 60 + "\n"
        self.assertEqual(bp.inspect_sidenotes(text, include_footnotes=False)[1], [])
        self.assertEqual(len(bp.inspect_sidenotes(text, include_footnotes=True)[1]), 1)


class EmissionTests(unittest.TestCase):
    def test_lengths_and_colours_are_literals(self):
        style = bp.resolve_style("report", {}, ["page.margin=2cm"], "zh")
        text = bp.typst_dict(style, bp.KNOBS)
        self.assertIn("margin: 2cm,", text)
        self.assertIn('rgb("#22645E")', text)
        self.assertNotIn('"2cm"', text)

    def test_font_list_emission(self):
        style = bp.resolve_style("report", {}, [], "en")
        text = bp.typst_dict(style, bp.KNOBS)
        self.assertIn('font: ("Libertinus Serif",)', text)

    def test_letter_snippet_keeps_linebreaks(self):
        snippet = bp.letter_snippet(
            {"letter": {"from": "示例公司\n示例部门", "to": "李四", "subject": "示例主题"}}
        )
        self.assertIn("#linebreak()", snippet)
        self.assertIn('has-from: "yes"', snippet)
        self.assertIn('has-date: "no"', snippet)
        self.assertIn("李四", snippet)

    def test_letter_snippet_escapes_quotes(self):
        snippet = bp.letter_snippet({"letter": {"from": '他说"你好"'}})
        self.assertIn('\\"你好\\"', snippet)

    def test_exported_spec_roundtrips_colours(self):
        style = bp.resolve_style("report", {}, ["color.accent=#ABCDEF"], "zh")
        text = bp.to_yaml(style)
        self.assertIn('accent: "#ABCDEF"', text)
        self.assertEqual(bp.parse_simple_yaml(text)["color"]["accent"], "#ABCDEF")


class SamplingTests(unittest.TestCase):
    def test_single_page(self):
        self.assertEqual(bp.pick_samples(1, "sample"), [1])

    def test_middle_page_skips_front_matter(self):
        self.assertEqual(bp.pick_samples(10, "sample"), [6])
        self.assertEqual(bp.pick_samples(4, "sample"), [3])
        self.assertEqual(bp.pick_samples(2, "sample"), [2])

    def test_all_pages(self):
        self.assertEqual(bp.pick_samples(3, "all"), [1, 2, 3])

    def test_zero(self):
        self.assertEqual(bp.pick_samples(0, "sample"), [])


class WarningTests(unittest.TestCase):
    def test_parses_typst_warning(self):
        stderr = (
            "warning: unknown font family: nope\n"
            "  ┌─ file.typ:1:2\n"
            "  │\n"
            "1 │ text\n"
            "  = hint: something\n"
        )
        warnings = bp.parse_warnings(stderr)
        self.assertEqual(len(warnings), 1)
        self.assertIn("unknown font family", warnings[0])

    def test_ignores_plain_output(self):
        self.assertEqual(bp.parse_warnings("compiled fine\n"), [])


class DetectTests(unittest.TestCase):
    def test_language_detection(self):
        self.assertEqual(bp.detect_lang("这是一段中文内容，用来判断语言。"), "zh")
        self.assertEqual(bp.detect_lang("This is an English paragraph about retention."), "en")


if __name__ == "__main__":
    unittest.main()
