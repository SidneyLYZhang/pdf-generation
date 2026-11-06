// Document assembly: page setup, show rules, front matter, body.

#let __header(st, meta) = context {
  let page-no = here().page()
  // Include headings that start on this page: at a chapter opening the
  // heading follows the header in document order, and the header should
  // already name the new chapter.
  let chapters = query(heading.where(level: 1)).filter(
    h => h.location().page() <= page-no,
  )
  let chapter = if chapters.len() > 0 { chapters.last().body } else { none }
  let title = if present(meta.has-title) { meta.title } else { none }
  let entry = none
  if st.furniture.header == "title" {
    entry = title
  } else if st.furniture.header == "chapter" {
    entry = if blank(chapter) { title } else { chapter }
  } else if st.furniture.header == "book" {
    entry = if calc.even(page-no) {
      if blank(title) { chapter } else { title }
    } else {
      if blank(chapter) { title } else { chapter }
    }
  }
  if blank(entry) {
    return
  }
  set text(size: 8.5pt, fill: st.color.muted, font: st.text.font)
  block(width: 100%, {
    align(left, entry)
    if st.furniture.header-rule {
      v(3pt)
      hairline(st)
    }
  })
}

#let __h1(it, st) = {
  if st.heading.page-break-before {
    pagebreak(weak: true)
  }
  if st.novel.chapter-prefix {
    novel-chapter(it, st)
  } else {
    set text(font: st.text.heading-font, size: st.heading.size-1, fill: st.heading.color, weight: "bold")
    block(width: 100%, {
      it
      if st.heading.rule {
        v(0.4em)
        hairline(st)
      }
    })
  }
}

#let __h2(it, st) = {
  set text(font: st.text.heading-font, size: st.heading.size-2, fill: st.heading.color, weight: "bold")
  it
}

#let __h3(it, st) = {
  set text(font: st.text.heading-font, size: st.heading.size-3, fill: st.heading.color, weight: "semibold")
  it
}

#let __code(it, st) = {
  let lang = it.lang
  block(
    width: 100%,
    fill: st.color.code-bg,
    radius: 2.5pt,
    stroke: none,
    inset: 0pt,
  )[
    #if st.code.header and lang != none [
      #block(
        width: 100%,
        inset: (x: 11pt, y: 5pt),
        stroke: (bottom: 0.5pt + st.color.rule),
      )[#text(size: 8pt, fill: st.color.muted, lang)]
    ]
    #block(inset: (x: 11pt, y: 9pt))[#text(size: st.code.size, it)]
  ]
}

#let __quote(it, st) = {
  block(
    width: 100%,
    inset: (left: 14pt, right: 8pt, top: 5pt, bottom: 5pt),
    stroke: (left: 2.2pt + st.color.accent),
  )[#text(fill: st.color.muted, it.body)]
}

#let doc(meta: (:), style: (:), body) = {
  let st = style
  st-state.update(st)

  let outside-numbers = st.furniture.page-number == "footer-outside"
  set page(
    ..paper-args(st),
    margin: page-margin(st),
    numbering: if outside-numbers { none } else { page-numbering(st) },
    number-align: number-align-of(st),
    header: if st.furniture.header == "none" { none } else { __header(st, meta) },
    footer: if outside-numbers {
      context {
        let p = here().page()
        align(
          if calc.odd(p) { right } else { left },
          text(
            size: 9pt,
            fill: st.color.muted,
            counter(page).display(st.furniture.page-number-format),
          ),
        )
      }
    } else {
      none
    },
  )
  set text(
    font: st.text.font,
    size: st.text.size,
    fill: st.color.ink,
    lang: st.text.lang,
    hyphenate: st.text.hyphenate,
  )
  set par(
    justify: st.text.justify,
    leading: st.text.leading,
    spacing: st.text.paragraph-spacing,
    linebreaks: "optimized",
  )
  // A `set` rule inside an `if` block would only affect that block, so the
  // conditional value is computed first.
  set par(first-line-indent: (amount: st.text.first-line-indent, all: true))
  set heading(
    numbering: if st.heading.numbering == "none" { none } else { st.heading.numbering },
  )
  show heading: set block(
    above: st.heading.space-before,
    below: st.heading.space-after,
  )
  show heading.where(level: 1): it => __h1(it, st)
  show heading.where(level: 2): it => __h2(it, st)
  show heading.where(level: 3): it => __h3(it, st)

  show link: it => text(fill: st.color.link, it)
  set terms(hanging-indent: 1.6em)
  set list(indent: 1.4em, body-indent: 0.5em)
  set enum(indent: 1.4em, body-indent: 0.5em)

  show figure.where(kind: table): set figure.caption(
    position: if st.float.table-caption == "top" { top } else { bottom },
  )
  show figure.where(kind: image): it => {
    set figure.caption(position: if st.float.figure-caption == "top" { top } else { bottom })
    set image(width: st.float.figure-width)
    it
  }
  set figure(numbering: if st.float.numbering == "none" { none } else { st.float.numbering })
  set math.equation(
    numbering: if st.math.numbering == "none" { none } else { st.math.numbering },
  )
  set table(
    stroke: (
      top: 0.8pt + st.color.rule,
      bottom: 0.8pt + st.color.rule,
      x: none,
      y: none,
    ),
    inset: (x: 6pt, y: 5pt),
  )
  set table.hline(stroke: 0.5pt + st.color.rule)
  show table.header: set text(weight: "bold")
  show figure.caption: it => text(size: 9pt, fill: st.color.muted, it)

  set raw(theme: if st.code.theme == "none" { none } else { auto })
  show raw.where(block: true): it => __code(it, st)
  show quote.where(block: true): it => __quote(it, st)

  if st.cover.enabled and present(meta.has-title) {
    cover-page(meta, st)
    pagebreak(weak: false)
  }
  if st.kind == "article" and present(meta.has-title) {
    article-head(meta, st)
  }
  if st.toc.enabled {
    toc-page(meta, st)
    pagebreak(weak: false)
  }
  if st.kind == "letter" {
    letter-head(meta, st)
  }

  body

  if st.kind == "letter" {
    letter-tail(meta, st)
  }
}
