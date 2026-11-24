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
// Page margins come in two axes, so a narrower measure can be bought without
// also squeezing the text block vertically.  `margin` remains the shorthand;
// files generated before the split only carry it, hence the defaults.
#let page-margin-x(st) = st.page.at("margin-x", default: st.page.margin)
#let page-margin-y(st) = st.page.at("margin-y", default: st.page.margin)

#let margin-parts(st) = {
  let base = page-margin-x(st)
  if st.note.style == "margin" {
    (inside: base + st.page.gutter, outside: base + st.note.width + st.note.gap)
  } else {
    (inside: base + st.page.gutter, outside: base)
  }
}

#let page-margin(st) = {
  let parts = margin-parts(st)
  let vertical = page-margin-y(st)
  if st.page.gutter == 0cm and st.note.style != "margin" and parts.inside == vertical {
    vertical
  } else {
    (inside: parts.inside, outside: parts.outside, top: vertical, bottom: vertical)
  }
}

#let number-align-of(st) = {
  let pos = st.furniture.page-number
  if pos == "none" { center } else if pos == "footer-right" { right } else { center }
}

// Paper dimensions live here once: `paper-args` derives Typst's page setup from
// the same table, and margin notes take the width as a length.
#let paper-table = (
  a4: (width: 210mm, height: 297mm, paper: "a4"),
  a5: (width: 148mm, height: 210mm, paper: "a5"),
  "6x9": (width: 6in, height: 9in),
  letter: (width: 8.5in, height: 11in, paper: "us-letter"),
)

#let paper-spec(st) = paper-table.at(st.page.paper, default: paper-table.a4)

#let paper-size(st) = {
  let spec = paper-spec(st)
  (width: spec.width, height: spec.height)
}

#let paper-args(st) = {
  let spec = paper-spec(st)
  if "paper" in spec { (paper: spec.paper) } else { (width: spec.width, height: spec.height) }
}

#let paper-width(st) = paper-size(st).width

#let page-numbering(st) = {
  if st.furniture.page-number == "none" { none } else { st.furniture.page-number-format }
}

#let hairline(st, weight: 0.6pt) = {
  line(length: 100%, stroke: weight + st.color.rule)
}

