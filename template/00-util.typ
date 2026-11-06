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

// Page margins: a symmetric margin, optionally with a binding gutter.
#let page-margin(st) = {
  let g = st.page.gutter
  if g == 0cm {
    st.page.margin
  } else {
    (
      inside: st.page.margin + g / 2,
      outside: st.page.margin - g / 2,
      top: st.page.margin,
      bottom: st.page.margin,
    )
  }
}

#let number-align-of(st) = {
  let pos = st.furniture.page-number
  if pos == "none" { center } else if pos == "footer-right" { right } else { center }
}

#let paper-args(st) = {
  let name = st.page.paper
  if name == "6x9" { (width: 6in, height: 9in) }
  else if name == "letter" { (paper: "us-letter") }
  else { (paper: name) }
}

#let page-numbering(st) = {
  if st.furniture.page-number == "none" { none } else { st.furniture.page-number-format }
}

#let hairline(st, weight: 0.6pt) = {
  line(length: 100%, stroke: weight + st.color.rule)
}

#let small-caps-label(body, st) = {
  text(size: 8.5pt, fill: st.color.muted, tracking: 0.06em, body)
}
