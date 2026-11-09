// Small helpers shared by every part of the template.

#let digits-cn = ("零", "一", "二", "三", "四", "五", "六", "七", "八", "九")

#let zh-num(n) = {
  if n <= 0 {
    str(n)
  } else if n < 10 {
    digits-cn.at(n)
  } else if n < 20 {
    "十" + (if calc.rem(n, 10) == 0 { "" } else { digits-cn.at(calc.rem(n, 10)) })
  } else if n < 100 {
    digits-cn.at(calc.div-euclid(n, 10)) + "十"
      + (if calc.rem(n, 10) == 0 { "" } else { digits-cn.at(calc.rem(n, 10)) })
  } else {
    str(n)
  }
}

// "None" and empty content are both treated as absent.
#let blank(x) = x == none or x == []

#let present(flag) = flag == "yes"

// Page margins: a symmetric margin, a binding gutter, and the extra outer
// column that margin notes need.  `inside`/`outside` make Typst mirror the
// two sides on odd/even pages.
#let margin-parts(st) = {
  let base = st.page.margin
  if st.note.style == "margin" {
    (inside: base + st.page.gutter, outside: base + st.note.width + st.note.gap)
  } else {
    (inside: base + st.page.gutter, outside: base)
  }
}

#let page-margin(st) = {
  let parts = margin-parts(st)
  if st.page.gutter == 0cm and st.note.style != "margin" {
    st.page.margin
  } else {
    (inside: parts.inside, outside: parts.outside, top: st.page.margin, bottom: st.page.margin)
  }
}

#let number-align-of(st) = {
  let pos = st.furniture.page-number
  if pos == "none" { center } else if pos == "footer-right" { right } else { center }
}

// Paper dimensions live here once: `paper-args` needs a name for Typst's page
// setup, margin notes need the width as a length.
#let paper-size(st) = {
  let name = st.page.paper
  if name == "a4" { (width: 210mm, height: 297mm) }
  else if name == "a5" { (width: 148mm, height: 210mm) }
  else if name == "6x9" { (width: 6in, height: 9in) }
  else if name == "letter" { (width: 8.5in, height: 11in) }
  else { (width: 210mm, height: 297mm) }
}

#let paper-args(st) = {
  let name = st.page.paper
  if name == "6x9" { (width: 6in, height: 9in) }
  else if name == "letter" { (paper: "us-letter") }
  else { (paper: name) }
}

#let paper-width(st) = paper-size(st).width

#let page-numbering(st) = {
  if st.furniture.page-number == "none" { none } else { st.furniture.page-number-format }
}

#let hairline(st, weight: 0.6pt) = {
  line(length: 100%, stroke: weight + st.color.rule)
}

