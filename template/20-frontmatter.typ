// Cover pages, article title block, table of contents, letter furniture.

#let cover-author-label(st) = {
  if st.kind == "report" { "报告人" }
  else if st.kind == "textbook" { "编者" }
  else { "作者" }
}

#let cover-meta-rows(meta, st) = {
  let rows = ()
  if meta.authors.len() > 0 {
    rows.push((cover-author-label(st), meta.authors.join("、")))
  }
  if present(meta.has-org) {
    rows.push(("机构", meta.org))
  }
  if present(meta.has-date) {
    rows.push(("日期", meta.date))
  }
  rows
}

#let cover-page(meta, st) = {
  let accent = st.color.accent
  if st.cover.style == "full" {
    page(header: none, footer: none, numbering: none, fill: accent)[
      #pad(left: 2.4cm, right: 2.4cm, top: 3.2cm, bottom: 2.6cm)[
        #grid(rows: (auto, 1fr, auto), {
          text(size: 9pt, fill: white, tracking: 0.18em, upper(st.kind))
        }, {
          v(2cm)
          if present(meta.has-title) [
            #text(size: 32pt, weight: "bold", fill: white, meta.title)
          ]
          if present(meta.has-subtitle) [
            #v(0.6cm)
            #text(size: 15pt, fill: white.transparentize(20%), meta.subtitle)
          ]
        }, {
          set text(size: 10.5pt, fill: white)
          for (k, v) in cover-meta-rows(meta, st) {
            v(0.25cm)
            text(v)
          }
        })
      ]
    ]
  } else {
    page(header: none, footer: none, numbering: none)[
      #grid(rows: (auto, 1fr, auto), {
        if st.cover.style == "band" {
          v(0.1cm)
          rect(width: 100%, height: 0.6cm, fill: accent)
        }
      }, {
        align(horizon)[
          #if present(meta.has-title) [
            #text(size: 30pt, weight: "bold", fill: st.color.ink, meta.title)
          ]
          #if present(meta.has-subtitle) [
            #v(0.55cm)
            #text(size: 14pt, fill: st.color.muted, meta.subtitle)
          ]
          #if st.cover.tagline != "" [
            #v(1.4cm)
            #text(size: 11pt, fill: accent, st.cover.tagline)
          ]
          #if st.cover.logo != "" [
            #v(1.2cm)
            #image(st.cover.logo, width: 3.2cm)
          ]
        ]
      }, {
        set text(size: 10.5pt, fill: st.color.muted)
        let rows = cover-meta-rows(meta, st)
        if rows.len() > 0 {
          grid(
            columns: (auto, 1fr),
            column-gutter: 1.2em,
            row-gutter: 0.42em,
            ..rows.map(((label, value)) => (
              text(fill: st.color.muted, size: 9pt, label),
              text(fill: st.color.ink, value),
            )).flatten(),
          )
        }
        v(0.5cm)
        if st.cover.style == "minimal" {
          line(length: 3cm, stroke: 0.8pt + accent)
        } else {
          hairline(st, weight: 0.8pt)
        }
      })
    ]
  }
}

#let article-head(meta, st) = {
  align(center)[
    #text(size: st.heading.size-1, weight: "bold", fill: st.color.ink, meta.title)
    #if present(meta.has-subtitle) [
      #v(0.4cm)
      #text(size: 13pt, fill: st.color.muted, meta.subtitle)
    ]
    #if meta.authors.len() > 0 [
      #v(0.9cm)
      #text(size: 11pt, meta.authors.join("、"))
    ]
    #if present(meta.has-org) [
      #v(0.25cm)
      #text(size: 10pt, fill: st.color.muted, meta.org)
    ]
    #if present(meta.has-date) [
      #v(0.25cm)
      #text(size: 10pt, fill: st.color.muted, meta.date)
    ]
  ]
  v(1.1cm)
  if present(meta.has-abstract) {
    block(
      width: 100%,
      inset: (x: 14pt, y: 11pt),
      fill: st.color.tint,
      radius: 2pt,
    )[
      #text(size: 9.5pt, weight: "bold", fill: st.color.accent, "摘要")
      #v(0.35em)
      #block(text(size: 10pt, meta.abstract))
      #if meta.keywords.len() > 0 [
        #v(0.5em)
        #text(size: 9pt, fill: st.color.muted, [关键词：] + meta.keywords.join("；"))
      ]
    ]
  }
  v(0.9cm)
}

#let toc-page(meta, st) = {
  align(left)[
    #text(size: 16pt, weight: "bold", fill: st.color.ink, st.toc.title)
    #v(0.15cm)
    #hairline(st)
  ]
  v(0.7cm)
  outline(title: none, depth: st.toc.depth, indent: 1.1em)
}

#let letter-head(meta, st) = {
  let l = meta.letter
  set text(size: st.text.size)
  if present(l.has-from) [
    #align(right)[
      #text(size: 9.5pt, fill: st.color.muted, l.from)
    ]
    #v(1.6cm)
  ]
  if present(l.has-date) [
    #align(right)[#text(size: 9.5pt, fill: st.color.muted, l.date)]
    #v(1cm)
  ]
  if present(l.has-to) [
    #block(l.to)
    #v(1.4cm)
  ]
  if present(l.has-subject) [
    #text(weight: "bold", l.subject)
    #v(0.9cm)
  ]
  if present(l.has-salutation) [
    #l.salutation
    #v(0.5cm)
  ]
}

#let letter-tail(meta, st) = {
  let l = meta.letter
  v(1.8cm)
  align(right)[
    #if present(l.has-closing) [#l.closing #linebreak()]
    #if present(l.has-signature) [#l.signature #linebreak()]
    #if present(l.has-date) [#text(size: 9.5pt, fill: st.color.muted, l.date)]
    #if not present(l.has-date) and present(meta.has-date) [#text(size: 9.5pt, fill: st.color.muted, meta.date)]
  ]
}
