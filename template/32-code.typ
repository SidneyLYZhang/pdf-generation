// Code line numbers.
//
// The rule is installed by `numbered-code`, never document-wide: a global
// `show raw.line` also numbers inline code (verified).  `numbered-code` is
// emitted by the filter around the blocks that want numbers, so per-block
// opt-in/opt-out and the global knob all end up as one wrapper.

#let numbered-code(body) = {
  show raw.line: it => context {
    let st = st-state.get()
    // Width of the widest line number in this block (e.g. "55" or "120"), so the
    // gutter stays put instead of shimmying as digits are added.
    let number-width = measure(text(size: st.code.size, str(it.count))).width
    // The grid is block-level; block spacing would separate every code line.
    block(
      above: 0pt,
      below: 0pt,
      grid(
        columns: (number-width, 1fr),
        column-gutter: 8pt,
        align: (right + top, left + top),
        text(size: st.code.size, fill: st.color.muted, str(it.number)),
        it.body,
      ),
    )
  }
  body
}
