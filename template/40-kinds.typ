// Novel-specific furniture: chapter opener counters and a first-paragraph
// dropped capital.

#let chapter-counter = counter("chapter")

// A dropped capital for the opening paragraph of a chapter.
//
// The parser hands over the plain text of the first paragraph of every
// chapter; for kinds that don't want a drop cap the text is rendered as a
// normal paragraph instead.
#let dropcap(txt) = context {
  let st = st-state.get()
  if not st.novel.dropcap {
    return par(txt)
  }
  layout(bounds => {
    if txt.len() < 6 {
      return par(txt)
    }
    let chars = txt.clusters()
    let letter = chars.at(0)
    let rest = chars.slice(1).join("")
    let letter-size = st.text.size * 2.5
    let letter-content = text(size: letter-size, weight: "bold", fill: st.color.accent, letter)
    let letter-width = measure(letter-content).width
    let gap = 5pt
    let target = measure(text(size: letter-size, letter)).height
    let avail = bounds.width - letter-width - gap
    if avail < 60pt {
      return par(txt)
    }

    // Take as much text as still fits next to the capital: the last line
    // beside it then reaches close to the normal measure instead of leaving
    // an orphan word.
    let probe(k) = {
      let part = rest.clusters().slice(0, k).join("")
      measure(box(width: avail, text(size: st.text.size, part))).height
    }
    let n = 8
    let limit = rest.len()
    while n + 2 < limit and probe(n + 2) <= target {
      n += 2
    }
    let beside = rest.clusters().slice(0, n).join("")
    let below = rest.clusters().slice(n).join("")

    set par(first-line-indent: 0em, justify: st.text.justify, leading: st.text.leading)
    block(width: 100%, {
      grid(
        columns: (letter-width, 1fr),
        column-gutter: gap,
        align: (left + top, left + top),
        letter-content,
        text(size: st.text.size, beside),
      )
      if below.len() > 0 {
        text(size: st.text.size, below)
      }
    })
  })
}

// Chapter opener: "第 N 章" over the chapter name, centred.
#let novel-chapter(it, st) = {
  chapter-counter.step()
  context {
    let n = chapter-counter.get().first()
    align(center)[
      #v(0.2cm)
      #text(size: 10pt, fill: st.color.muted, tracking: 0.22em, [第 #zh-num(n) 章])
      #v(0.7em)
      #text(size: st.heading.size-1, weight: "bold", fill: st.heading.color, it.body)
      #v(0.3cm)
      #line(length: 2.2cm, stroke: 0.8pt + st.color.accent)
    ]
  }
  v(1.6em)
}
