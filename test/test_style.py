"""Unit tests for style parsing and resolution (no typst/pandoc needed)."""

from __future__ import annotations

import re
import shutil
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

    # Measured from a 300 ppi probe: the bundled CJK body font lays out an 8.00pt
    # line box at 11pt, so what a reader experiences is (line box + leading) /
    # size -- not 1 + leading.  This is the Chinese-prose range; Western prose
    # has its own, lower comfortable range and is not asserted here.
    LINE_BOX_EM = 8.0 / 11.0

    def _leading_factor(self, kind: str) -> float:
        style = bp.resolve_style(kind, {}, [], "zh")
        size = bp.length_pt(style["text"]["size"], 11.0)
        lead = bp.length_pt(style["text"]["leading"], size)
        return (self.LINE_BOX_EM * size + lead) / size

    def test_every_kind_leading_sits_in_the_chinese_range(self):
        for kind in bp.KINDS:
            with self.subTest(kind=kind):
                self.assertGreaterEqual(self._leading_factor(kind), 1.4)
                self.assertLessEqual(self._leading_factor(kind), 1.75)

    def test_indented_kinds_use_only_the_typst_minimum_gap(self):
        # Indent or paragraph spacing, never both: indented Kinds pin the gap at
        # Typst's floor and let the indent alone mark the break.  Anything above
        # the floor becomes a second way of separating paragraphs.
        for kind in ("book", "textbook", "novel"):
            with self.subTest(kind=kind):
                style = bp.resolve_style(kind, {}, [], "zh")
                self.assertEqual(style["text"]["first-line-indent"], "2em")
                self.assertEqual(style["text"]["paragraph-spacing"], "4.5pt")

    def test_spaced_kinds_separate_paragraphs_more_than_lines(self):
        for kind in ("report", "article", "letter", "note"):
            style = bp.resolve_style(kind, {}, [], "zh")
            size = bp.length_pt(style["text"]["size"], 11.0)
            lead = bp.length_pt(style["text"]["leading"], size)
            gap = bp.length_pt(style["text"]["paragraph-spacing"], size)
            self.assertGreater(gap, lead, kind)

    def test_letter_heading_reaches_thirty_percent_above_body(self):
        style = bp.resolve_style("letter", {}, [], "zh")
        body = bp.length_pt(style["text"]["size"], 11.0)
        head = bp.length_pt(style["heading"]["size-1"], body)
        self.assertGreaterEqual(head / body, 1.3 - 1e-9)

    def test_english_a4_gets_a_narrower_measure(self):
        en = bp.resolve_style("report", {}, [], "en")
        zh = bp.resolve_style("report", {}, [], "zh")
        self.assertEqual(en["page"]["margin-x"], "4.8cm")
        # Only the horizontal axis moves: the text block keeps its height.
        self.assertEqual(en["page"]["margin-y"], "2.5cm")
        self.assertEqual(zh["page"]["margin-x"], "2.5cm")

    def test_margin_axes_default_to_the_single_margin(self):
        style = bp.resolve_style("report", {}, ["page.margin=2cm"], "zh")
        self.assertEqual(style["page"]["margin-x"], "2cm")
        self.assertEqual(style["page"]["margin-y"], "2cm")
        one_axis = bp.resolve_style("report", {}, ["page.margin-x=1.5cm"], "zh")
        self.assertEqual(one_axis["page"]["margin-x"], "1.5cm")
        self.assertEqual(one_axis["page"]["margin-y"], "2.5cm")

    def test_pinning_the_vertical_axis_keeps_the_english_rule_on(self):
        # Asking for a tighter top margin is not a request to keep a 100-character
        # line; only the axis the author touched is off limits.
        style = bp.resolve_style("report", {}, ["page.margin-y=2cm"], "en")
        self.assertEqual(style["page"]["margin-y"], "2cm")
        self.assertEqual(style["page"]["margin-x"], bp.ENGLISH_MARGIN_X)

    def test_explicit_auto_still_means_no_opinion(self):
        auto = bp.resolve_style("report", {}, ["page.margin-x=auto"], "en")
        pinned = bp.resolve_style("report", {}, ["page.margin-x=2cm"], "en")
        self.assertEqual(auto["page"]["margin-x"], bp.ENGLISH_MARGIN_X)
        self.assertEqual(pinned["page"]["margin-x"], "2cm")

    def test_english_measure_lands_in_comfortable_character_count(self):
        style = bp.resolve_style("report", {}, [], "en")
        a4_width = 210 / 25.4 * 72
        margin = bp.length_pt(style["page"]["margin-x"], 11.0)
        size = bp.length_pt(style["text"]["size"], 11.0)
        # Running prose in Libertinus averages at most 0.42em per character;
        # the wide bound keeps this assertion from overstating the result.
        chars = (a4_width - 2 * margin) / (0.42 * size)
        self.assertGreaterEqual(chars, 60)
        self.assertLessEqual(chars, 75)

    def test_compact_kinds_keep_their_dense_page_in_english(self):
        # `note` is defined by a dense page, so the English measure rule must not
        # widen it; the build warning reports the wide measure instead.
        note = bp.resolve_style("note", {}, [], "en")
        self.assertEqual(note["page"]["margin"], "2.5cm")

    def test_explicit_margin_beats_english_default(self):
        by_set = bp.resolve_style("report", {}, ["page.margin=2cm"], "en")
        by_doc = bp.resolve_style("report", {"style": {"page": {"margin": "3cm"}}}, [], "en")
        self.assertEqual(by_set["page"]["margin"], "2cm")
        self.assertEqual(by_doc["page"]["margin"], "3cm")


class PrincipleCheckTests(unittest.TestCase):
    def check(self, kind: str, *sets: str, level: int = 0,
              lang: str = "zh") -> tuple[list[str], list[str]]:
        notes: list[str] = []
        warnings: list[str] = []
        style = bp.resolve_style(kind, {}, list(sets), lang, notes)
        bp.check_principles(style, {}, max_heading_level=level, notes=notes, warnings=warnings)
        return notes, warnings

    def test_defaults_pass_every_rule(self):
        for lang in ("zh", "en"):
            for kind in bp.KINDS:
                with self.subTest(kind=kind, lang=lang):
                    _, warnings = self.check(kind, level=3, lang=lang)
                    self.assertEqual(warnings, [])

    def test_indent_with_visible_spacing_is_refused(self):
        with self.assertRaises(bp.SpecError) as caught:
            self.check("book", "text.paragraph-spacing=8pt")
        self.assertIn("indent-and-spacing", str(caught.exception))
        self.assertIn("改法", str(caught.exception))

    def test_tight_spacing_without_indent_is_refused(self):
        with self.assertRaises(bp.SpecError) as caught:
            self.check("report", "text.paragraph-spacing=6pt")
        self.assertIn("spacing-below-leading", str(caught.exception))

    def test_deviation_waives_the_rule_and_is_announced(self):
        style = bp.resolve_style("book", {}, ["text.paragraph-spacing=8pt"], "zh")
        notes: list[str] = []
        bp.check_principles(
            style,
            {"indent-and-spacing": {"source": "standard", "reason": "期刊模板要求段间空一行"}},
            notes=notes,
        )
        self.assertIn("已放行偏离 indent-and-spacing", notes[0])
        self.assertIn("机构规范", notes[0])

    def test_line_height_outside_the_band_is_a_warning(self):
        notes, warnings = self.check("report", "text.leading=0.55em")
        self.assertEqual(notes, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("[line-height]", warnings[0])
        self.assertIn("1.28×", warnings[0])
        low, high = bp.CHINESE_LEADING
        self.assertIn(f"{low:.2f}–{high:.2f}×", warnings[0])

    def test_western_prose_is_not_held_to_the_chinese_band(self):
        notes, warnings = self.check("report", "text.leading=0.55em", lang="en")
        self.assertEqual(warnings, [])
        self.assertTrue(any("西文跳过 line-height" in note for note in notes))

    def test_unknown_font_stack_degrades_to_a_note(self):
        notes, warnings = self.check(
            "report", 'text.font=["Noto Sans SC"]', "text.leading=0.55em"
        )
        self.assertEqual(warnings, [])
        self.assertTrue(any("字族不在实测范围内" in note for note in notes))

    def test_measure_outside_the_band_is_a_warning(self):
        _, warnings = self.check("report", "text.size=8pt")
        self.assertEqual(len(warnings), 1)
        self.assertIn("[measure]", warnings[0])
        low, high = bp.CHINESE_MEASURE
        self.assertIn(f"{low}–{high}", warnings[0])

    def test_short_form_kinds_are_exempt_from_the_measure_band(self):
        # A letter is read in one sitting; 88 characters a line is not a defect.
        for kind in ("letter", "note"):
            with self.subTest(kind=kind):
                _, warnings = self.check(kind, "page.margin=1cm", lang="en")
                self.assertEqual(warnings, [])

    def test_english_measure_outside_the_band_is_a_warning(self):
        _, warnings = self.check("report", "page.margin=1cm", lang="en")
        self.assertEqual(len(warnings), 1)
        self.assertIn("[measure]", warnings[0])
        low, high = bp.WESTERN_MEASURE
        self.assertIn(f"{low}–{high}", warnings[0])

    def test_heading_ratio_below_one_third_is_a_warning(self):
        _, warnings = self.check("report", "heading.size-1=13pt")
        self.assertEqual(len(warnings), 1)
        self.assertIn("[heading-ratio]", warnings[0])
        self.assertIn("1.18", warnings[0])

    def test_heading_depth_over_four_is_a_warning(self):
        _, warnings = self.check("report", level=5)
        self.assertEqual(len(warnings), 1)
        self.assertIn("[heading-depth]", warnings[0])
        self.assertIn("5 级", warnings[0])

    def test_heading_depth_at_four_is_fine(self):
        _, warnings = self.check("report", level=4)
        self.assertEqual(warnings, [])

    def test_heading_depth_ignores_headings_inside_code_fences(self):
        text = "# 一\n\n```markdown\n##### 这是示例，不是标题\n```\n\n## 二\n"
        self.assertEqual(bp.heading_depth(text), 2)

    def test_heading_depth_reads_both_markdown_and_typst_markup(self):
        self.assertEqual(bp.heading_depth("# 一\n\n### 三\n"), 3)
        self.assertEqual(bp.heading_depth("= 一\n\n=== 三\n"), 3)
        self.assertEqual(bp.heading_depth("正文，没有标题。\n"), 0)

    def test_warning_rule_cannot_be_bought_off_with_a_deviation(self):
        with self.assertRaises(bp.SpecError) as caught:
            bp.deviations_of(
                {"deviations": {"line-height": {"source": "user", "reason": "就这样"}}}
            )
        self.assertIn("写进交付的排版方案", str(caught.exception))

    def test_paper_sizes_match_the_template(self):
        # The measure estimate needs its own table, but two copies drift: the
        # template's paper-table is the one Typst actually lays out with.
        source = (ROOT / "template" / "00-util.typ").read_text(encoding="utf-8")
        found = {}
        for name, width, unit_w, height, unit_h in re.findall(
            r'^\s+"?([\w]+)"?: \(width: ([\d.]+)(mm|in), height: ([\d.]+)(mm|in)',
            source,
            re.M,
        ):
            scale = {"mm": 1.0, "in": 25.4}
            found[name] = (float(width) * scale[unit_w], float(height) * scale[unit_h])
        self.assertEqual(set(found), set(bp.PAPER_MM))
        for name, (width, height) in bp.PAPER_MM.items():
            with self.subTest(paper=name):
                self.assertAlmostEqual(found[name][0], width, places=1)
                self.assertAlmostEqual(found[name][1], height, places=1)

    def test_deviation_must_name_a_known_rule(self):
        with self.assertRaises(bp.SpecError):
            bp.deviations_of({"deviations": {"no-such-rule": {"source": "user", "reason": "x"}}})

    def test_deviation_must_carry_a_reason(self):
        with self.assertRaises(bp.SpecError):
            bp.deviations_of({"deviations": {"indent-and-spacing": {"source": "user", "reason": " "}}})

    def test_deviation_source_is_checked(self):
        with self.assertRaises(bp.SpecError):
            bp.deviations_of(
                {"deviations": {"indent-and-spacing": {"source": "同事", "reason": "说好的"}}}
            )

    def test_style_literal_is_read_back_from_generated_typst(self):
        text = (
            "#let style = (\n"
            "  page: (\n"
            '  paper: "a4",\n'
            "  margin: 2.5cm,\n"
            "),\n"
            "  text: (\n"
            '  font: ("Libertinus Serif", "Noto Serif SC",),\n'
            "  size: 11pt,\n"
            "  leading: 0.75em,\n"
            "  paragraph-spacing: 6pt,\n"
            "  first-line-indent: 0em,\n"
            "  justify: true,\n"
            "),\n"
            "  heading: (\n"
            "  size-1: 22pt,\n"
            "),\n"
            ")\n"
        )
        style = bp.parse_style_literal(text)
        self.assertEqual(style["page"]["paper"], "a4")
        self.assertEqual(style["text"]["font"], ["Libertinus Serif", "Noto Serif SC"])
        self.assertEqual(style["text"]["paragraph-spacing"], "6pt")
        self.assertIs(style["text"]["justify"], True)
        # 6pt is tighter than the 8.25pt leading, so the .typ is refused too.
        with self.assertRaises(bp.SpecError):
            bp.check_principles(style, {})

    def test_style_literal_without_a_style_block_is_refused(self):
        with self.assertRaises(bp.SpecError) as caught:
            bp.parse_style_literal("// 手写的文件\n")
        self.assertIn("typst compile", str(caught.exception))

    def test_unreadable_length_is_refused_rather_than_read_as_zero(self):
        # `2ch` has no point equivalent here; reading it as 0 would look like
        # "no indent" and quietly pass the very rule that should fire.
        text = (
            "#let style = (\n  text: (\n  size: 11pt,\n  leading: 0.75em,\n"
            "  paragraph-spacing: 1em,\n  first-line-indent: 2ch,\n),\n)\n"
        )
        with self.assertRaises(bp.SpecError) as caught:
            bp.check_principles(bp.parse_style_literal(text), {})
        self.assertIn("first-line-indent", str(caught.exception))

    def test_deviation_written_into_the_typ_header_is_honoured(self):
        text = (
            '#let style = (\n  text: (\n  size: 11pt,\n  leading: 0.75em,\n'
            "  paragraph-spacing: 6pt,\n  first-line-indent: 0em,\n),\n)\n"
            '// pdfgen-deviation: {"rule": "spacing-below-leading", "source": "user", '
            '"reason": "客户模板要求段间不留空隙"}\n'
        )
        declared = bp.deviations_from_typ(text)
        self.assertEqual(declared["spacing-below-leading"]["reason"], "客户模板要求段间不留空隙")
        bp.check_principles(bp.parse_style_literal(text), declared)

    def test_two_rule_hints_do_not_send_the_reader_in_a_circle(self):
        # Each hint has to name a path that satisfies the other rule as well:
        # the indent rule offers the floor, the spacing rule offers a taller gap
        # and says what to do with the indent if the reader picks that way.
        with self.assertRaises(bp.SpecError) as caught:
            self.check("report", "text.paragraph-spacing=6pt")
        self.assertIn("提到", str(caught.exception))
        self.assertIn(f"降回 {bp.PARAGRAPH_SPACING_FLOOR}", str(caught.exception))
        with self.assertRaises(bp.SpecError) as caught:
            self.check("book", "text.paragraph-spacing=8pt")
        self.assertIn(f"降到 {bp.PARAGRAPH_SPACING_FLOOR}", str(caught.exception))


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


class MathStyleTests(unittest.TestCase):
    def test_book_and_article_number_equations(self):
        self.assertEqual(bp.resolve_style("book", {}, [], "zh")["math"]["numbering"], "(1)")
        self.assertEqual(bp.resolve_style("article", {}, [], "zh")["math"]["numbering"], "(1)")

    def test_other_kinds_do_not_number(self):
        for kind in bp.KINDS:
            if kind in ("book", "article"):
                continue
            self.assertEqual(bp.resolve_style(kind, {}, [], "zh")["math"]["numbering"], "none")

    def test_numbering_can_be_turned_off_or_changed(self):
        self.assertEqual(
            bp.resolve_style("book", {}, ["math.numbering=none"], "zh")["math"]["numbering"], "none"
        )
        self.assertEqual(
            bp.resolve_style("report", {}, ["math.numbering=1"], "zh")["math"]["numbering"], "1"
        )


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


class DiagramScanTests(unittest.TestCase):
    def test_parse_fence_info(self):
        self.assertEqual(
            bp.parse_fence_info('dot {caption="数据流" width=60%}'),
            ("dot", {"caption": "数据流", "width": "60%"}),
        )
        self.assertEqual(bp.parse_fence_info("mermaid"), ("mermaid", {}))
        lang, attrs = bp.parse_fence_info('dot {#fig:a caption="x"}')
        self.assertEqual(lang, "dot")
        self.assertEqual(attrs["id"], "fig:a")
        self.assertEqual(attrs["caption"], "x")

    def test_iter_fences_handles_tilde_fences_and_indentation(self):
        text = "说明\n\n  ~~~dot\n  digraph { A -> B; }\n  ~~~\n\n结尾\n"
        fences = list(bp.iter_fences(text))
        self.assertEqual(len(fences), 1)
        start, end, indent, info, body = fences[0]
        self.assertEqual((start, end), (3, 5))
        self.assertEqual((indent, info.strip()), (2, "dot"))
        self.assertEqual(body, ["digraph { A -> B; }"])
        self.assertNotIn("digraph", bp.prose_only(text))

    def test_line_numbers_reported_for_diagram_blocks(self):
        text = "第一段\n\n```dot\n digraph { A -> B; }\n```\n"
        blocks = bp.find_diagram_blocks(text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["line"], 3)

    @unittest.skipUnless(shutil.which("dot"), "需要 graphviz")
    def test_dot_argv_asks_for_svg(self):
        argv = bp.renderer_argv("dot", Path("a.dot"), Path("a.svg"))
        self.assertIn("-Tsvg", argv)
        self.assertIn("a.dot", " ".join(argv))


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
