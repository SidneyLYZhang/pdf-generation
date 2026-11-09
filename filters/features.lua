-- Metadata-driven AST rewrites.  These run before semantic.lua turns fenced
-- Divs into raw Typst, so they also reach code blocks and footnotes that sit
-- inside a `::: {.notice}` (a single filter could not: its `Pandoc` function
-- runs after the Div handler has already flattened the content).

local function typst_body(blocks, meta)
  local doc = pandoc.Pandoc(blocks, meta or pandoc.Meta{})
  return pandoc.write(doc, "typst"):gsub("%s+$", "")
end

-- In margin mode every footnote becomes a margin note.  A `show footnote` rule
-- in the template is not enough: it replaces the inline marker, but Typst still
-- typesets the entry in the page footer.
local function note_to_sidenote(note)
  return pandoc.RawInline("typst", "#sidenote[" .. typst_body(note.content) .. "]")
end

-- Line numbers are opt-in: the global knob wraps every code block, a per-block
-- class overrides either way.  The wrapper installs a local `show raw.line`, so
-- inline code is never numbered.
local function numbered_code_block(el)
  return pandoc.RawBlock(
    "typst",
    "#numbered-code[\n" .. typst_body({ el }) .. "\n]"
  )
end

function Pandoc(doc)
  local note_style = doc.meta["pdfgen-note-style"]
  note_style = note_style and pandoc.utils.stringify(note_style) or "footnote"
  if note_style == "margin" then
    doc = doc:walk({ Note = note_to_sidenote })
  end

  local code_lines = doc.meta["pdfgen-code-lines"]
  code_lines = code_lines and pandoc.utils.stringify(code_lines) == "yes"
  doc = doc:walk({
    CodeBlock = function(el)
      if el.classes:includes("no-line-numbers") then
        return nil
      end
      if code_lines or el.classes:includes("line-numbers") then
        return numbered_code_block(el)
      end
      return nil
    end,
  })
  return doc
end
