-- Line 1-6: the AST-level syntax this filter owns.  Metadata-driven rewrites
-- (margin notes, code line numbers, diagrams) live in features.lua and
-- diagrams.lua, which run first.
--   fenced divs -> semantic blocks / page breaks / margin notes
--   spans       -> inline margin notes
--   Cite        -> cross-references (fig:/tab:/eq:/sec:) vs citations
--   Str         -> textual \eqref{…} / \ref{…} cross-references
--   Pandoc      -> kind-specific rewrites (novel drop caps)
--
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

local function typst_inlines(inlines)
  return typst_body({ pandoc.Plain(inlines) })
end

-- `[文字]{.sidenote}` and `::: {.sidenote}` are margin notes.  One class name
-- for both: the element type says which one it is.
function Span(el)
  if el.classes:includes("sidenote") then
    return pandoc.RawInline("typst", "#sidenote[" .. typst_inlines(el.content) .. "]")
  end
  return nil
end

function Div(el)
  if el.classes:includes("pagebreak") then
    return pandoc.RawBlock("typst", "#pagebreak()")
  end

  if el.classes:includes("sidenote") then
    return pandoc.RawBlock("typst", "#sidenote-block[\n" .. typst_body(el.content) .. "\n]")
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

-- `@fig:x` / `@tab:x` / `@eq:x` / `@sec:x` are cross-references; every other
-- `@id` is a citation.  pandoc parses both into Cite nodes, so the split lives
-- here in the AST instead of being a regex over the document text.
local REF_PREFIXES = { "fig:", "tab:", "eq:", "sec:" }

local function is_reference(id)
  for _, prefix in ipairs(REF_PREFIXES) do
    if id:sub(1, #prefix) == prefix then
      return true
    end
  end
  return false
end

function Cite(el)
  if #el.citations == 0 then
    return nil
  end
  for _, citation in ipairs(el.citations) do
    if not is_reference(citation.id) then
      return nil
    end
  end

  local out = {}
  for index, citation in ipairs(el.citations) do
    if index > 1 then
      out[#out + 1] = pandoc.Str(",")
      out[#out + 1] = pandoc.Space()
    end
    -- Typst labels only allow word characters, `:`, `.` and `-`.
    local target = citation.id:gsub("[^%w_:%.%-]", "")
    out[#out + 1] = pandoc.RawInline("typst", "#ref(<" .. target .. ">)")
    local suffix = pandoc.utils.stringify(citation.suffix)
    if suffix ~= "" then
      out[#out + 1] = pandoc.Space()
      out[#out + 1] = pandoc.Str(suffix)
    end
  end
  return out
end

-- `\eqref{eq:x}` and `\ref{eq:x}` are LaTeX cross-reference syntax.  Our dialect
-- turns off `raw_tex`, so they arrive as ordinary text; rewrite them here into
-- the same `#ref` the `@fig:` form produces.  (Lua patterns have no `|`, so the
-- command name is captured and checked.)
local LABEL_CHARS = "[%w_:%.%-]"
local REF_PATTERN = "\\(%a+)%{(" .. LABEL_CHARS .. "+)%}"
local REF_COMMANDS = { eqref = true, ref = true }

local function ref_inline(target)
  return pandoc.RawInline("typst", "#ref(<" .. target .. ">)")
end

function Str(el)
  if not el.text:find("\\", 1, true) then
    return nil
  end
  local out = {}
  local scan, flush = 1, 1
  local changed = false
  while true do
    local start, finish, command, target = el.text:find(REF_PATTERN, scan)
    if not start then
      break
    end
    scan = finish + 1
    if REF_COMMANDS[command] then
      if start > flush then
        out[#out + 1] = pandoc.Str(el.text:sub(flush, start - 1))
      end
      out[#out + 1] = ref_inline(target)
      changed = true
      flush = scan
    end
  end
  if not changed then
    return nil
  end
  if flush <= #el.text then
    out[#out + 1] = pandoc.Str(el.text:sub(flush))
  end
  return out
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
    return doc
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
