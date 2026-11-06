#let meta = (
  has-title: "$if(title)$yes$else$no$endif$",
  has-subtitle: "$if(subtitle)$yes$else$no$endif$",
  has-abstract: "$if(abstract)$yes$else$no$endif$",
  has-date: "$if(date)$yes$else$no$endif$",
  has-org: "$if(org)$yes$else$no$endif$",
  title: [$if(title)$$title$$endif$],
  subtitle: [$if(subtitle)$$subtitle$$endif$],
  authors: ($for(author)$[$author$],$endfor$),
  org: [$if(org)$$org$$endif$],
  date: [$if(date)$$date$$endif$],
  abstract: [$if(abstract)$$abstract$$endif$],
  keywords: ($for(keywords)$[$keywords$],$endfor$),
)
