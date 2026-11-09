// Margin notes (sidenotes).
//
// A note is placed in the outer margin at the anchor's line.  `page-margin`
// widens that margin whenever `note.style` is "margin", so the note never
// eats into the text column.
//
// Two details make this work:
//   * the note sits in a zero-width `box`: a bare `place` is block-level and
//     would split the paragraph at every note;
//   * `here().position().x` is a page coordinate, so the note can be pushed to
//     a fixed x regardless of where in the line it is anchored.
//
// Two notes anchored on the same line overlap: Typst has no margin-note float
// that reserves space.  The build warns when a paragraph carries more than one.

#let __note-body(body, st) = text(size: st.note.size, fill: st.color.muted, body)

// Page x (from the page's left edge) of the note's left edge.
#let __note-x(st, page-no) = {
  let parts = margin-parts(st)
  if st.page.gutter > 0cm and calc.even(page-no) {
    // Two-sided: on even pages the outer margin is the left one.
    parts.outside - st.note.gap - st.note.width
  } else {
    parts.inside + (paper-width(st) - parts.inside - parts.outside) + st.note.gap
  }
}

// `dx` is relative to the note's parent: the anchor for an inline note, the
// text column's left edge for a block one.  The two callers differ because
// `here().position()` reports page coordinates inline but not for blocks.
#let __note-place(body, st, dx) = {
  box(
    width: 0pt,
    place(dx: dx, block(width: st.note.width, __note-body(body, st))),
  )
}

#let sidenote(body) = context {
  let st = st-state.get()
  if st.note.style == "margin" {
    __note-place(body, st, __note-x(st, here().page()) - here().position().x)
  } else {
    // Explicit marker with `note.style=footnote`: keep the text, move it to
    // the page footer instead of dropping it.
    footnote(body)
  }
}

#let sidenote-block(body) = context {
  let st = st-state.get()
  if st.note.style == "margin" {
    let edge = margin-parts(st).inside
    block(width: 100%, __note-place(body, st, __note-x(st, here().page()) - edge))
  } else {
    block(footnote(body))
  }
}
