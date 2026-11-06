// Semantic blocks (theorem, definition, example, exercise, notice, warning).
// They are called from the parsed body, i.e. outside doc()'s lexical scope, so
// the active Style spec travels through a state.

#let st-state = state("pdfgen-style", (:))
#let sem-counter = counter("sem")

#let __sem(label, body, title: none, numbered: true, st: (:)) = {
  let show-number = numbered and st.semantic.numbering != "none"
  if show-number { sem-counter.step() }
  block(
    width: 100%,
    above: 0.95em,
    below: 0.95em,
    inset: (left: 13pt, right: 11pt, top: 9pt, bottom: 9pt),
    fill: st.color.tint,
    radius: 2.5pt,
    stroke: (left: 2.4pt + st.color.accent),
  )[
    #text(weight: "bold", fill: st.color.accent)[#label#if show-number [ #context sem-counter.display("1")]#if title != none [：#title]]
    #v(0.45em)
    #body
  ]
}

#let thm(title: none, body) = context __sem("定理", body, title: title, st: st-state.get())
#let defn(title: none, body) = context __sem("定义", body, title: title, st: st-state.get())
#let lemma(title: none, body) = context __sem("引理", body, title: title, st: st-state.get())
#let prop(title: none, body) = context __sem("命题", body, title: title, st: st-state.get())
#let example(title: none, body) = context __sem("例题", body, title: title, st: st-state.get())
#let exercise(title: none, body) = context __sem("习题", body, title: title, st: st-state.get())
#let notice(body) = context __sem("提示", body, numbered: false, st: st-state.get())
#let warning(body) = context __sem("注意", body, numbered: false, st: st-state.get())

#let proof(body) = context {
  let st = st-state.get()
  block(width: 100%, above: 0.7em, below: 0.7em)[
    #text(weight: "bold", fill: st.color.muted, "证明")
    #h(0.4em)
    #body
    #h(0.4em)
    #text(fill: st.color.muted, "∎")
  ]
}
