-- Map fenced Divs to the semantic blocks the template provides, and mark the
-- first paragraph of each chapter so the template can drop a capital.
-- Anything unknown falls through to pandoc's default `#block[...]`, so the
-- content is never lost.

local blocks = {
  theorem = "thm",
  definition = "defn",
  lemma = "lemma",
  proposition = "prop",
  example = "example",
  exercise = "exercise",
  proof = "proof",
  notice = "notice",
  tip = "notice",
  warning = "warning",
  caution = "warning",
}

local function typst_body(el_blocks, meta)
  local doc = pandoc.Pandoc(el_blocks, meta or pandoc.Meta{})
  return pandoc.write(doc, "typst"):gsub("%s+$", "")
end

function Div(el)
  if el.classes:includes("pagebreak") then
    return pandoc.RawBlock("typst", "#pagebreak()")
  end

  local target = nil
  for _, cls in ipairs(el.classes) do
    if blocks[cls] then
      target = blocks[cls]
      break
    end
  end
  if not target then
    return nil
  end

  local title = el.attributes["title"]
  local head = ""
  if title and title ~= "" then
    head = "(title: [" .. title .. "])"
  end
  return pandoc.RawBlock("typst", "#" .. target .. head .. "[\n" .. typst_body(el.content) .. "\n]")
end

-- The novel kind drops the first character of every chapter opening; the
-- template turns this wrapper into a drop cap and ignores it otherwise.
-- Only plain-text paragraphs qualify: stringifying would silently drop bold,
-- links and other inline markup.
local function plain_paragraph(para)
  for _, inline in ipairs(para.content) do
    local t = inline.t
    if t ~= "Str" and t ~= "Space" and t ~= "SoftBreak" then
      return false
    end
  end
  return true
end

function Pandoc(doc)
  local kind = doc.meta["pdfgen-kind"]
  kind = kind and pandoc.utils.stringify(kind) or ""
  if kind ~= "novel" then
    return nil
  end

  local out = {}
  local pending = false
  for _, block in ipairs(doc.blocks) do
    if pending and block.t == "Para" and plain_paragraph(block) then
      local txt = pandoc.utils.stringify(block)
        :gsub("\\", "\\\\")
        :gsub('"', '\\"')
      out[#out + 1] = pandoc.RawBlock("typst", '#dropcap("' .. txt .. '")')
      pending = false
    else
      out[#out + 1] = block
      pending = block.t == "Header" and block.level == 1
    end
  end
  doc.blocks = out
  return doc
end
