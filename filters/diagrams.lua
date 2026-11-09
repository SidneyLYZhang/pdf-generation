-- Diagrams rendered by the build.
--
-- `pdfgen-diagrams` (passed with --metadata-file) maps the 1-based index of each
-- diagram fence to its SVG.  Counting and looking up by position, rather than by
-- code text, keeps two identical diagrams distinct and never touches a block
-- that merely contains diagram source as an example.

local function text_of(entry, name)
  local value = entry[name]
  if value == nil then
    return nil
  end
  local text = pandoc.utils.stringify(value)
  if text == "" then
    return nil
  end
  return text
end

-- A Typst string literal: quotes and backslashes escaped, no raw newlines.
local function typst_string(value)
  local escaped = value
    :gsub("\\", "\\\\")
    :gsub('"', '\\"')
    :gsub("\r", "\\r")
    :gsub("\n", "\\n")
  return '"' .. escaped .. '"'
end

local function diagram_lang(el)
  local lang = el.classes[1]
  if lang == "dot" or lang == "mermaid" then
    return lang
  end
  return nil
end

local function render_figure(entry)
  local image = "image(" .. typst_string(text_of(entry, "path"))
  local width = text_of(entry, "width")
  if width then
    image = image .. ", width: " .. width
  end
  image = image .. ")"
  local figure = "#figure(" .. image
  local caption = text_of(entry, "caption")
  if caption then
    figure = figure .. ", caption: [#text(" .. typst_string(caption) .. ")]"
  end
  figure = figure .. ")"
  local label = text_of(entry, "id")
  if label then
    figure = figure .. "<" .. label .. ">"
  end
  return pandoc.RawBlock("typst", figure)
end

-- No renderer for this language: show the source, but keep the figure so the
-- caption, the number and `@fig:` references still work.
local function source_figure(el, entry)
  local caption = text_of(entry, "caption")
  local label = text_of(entry, "id")
  if caption == nil and label == nil then
    return nil
  end
  local inner = pandoc.write(pandoc.Pandoc({ el }), "typst"):gsub("%s+$", "")
  local figure = "#figure(\n" .. inner .. "\n"
  if caption then
    figure = figure .. ", caption: [#text(" .. typst_string(caption) .. ")]"
  end
  figure = figure .. ")"
  if label then
    figure = figure .. "<" .. label .. ">"
  end
  return pandoc.RawBlock("typst", figure)
end

function Pandoc(doc)
  local map = doc.meta["pdfgen-diagrams"]
  if map == nil then
    return doc
  end
  local index = 0
  return doc:walk({
    CodeBlock = function(el)
      if not diagram_lang(el) then
        return nil
      end
      index = index + 1
      local entry = map[tostring(index)]
      if entry == nil then
        return nil
      end
      if text_of(entry, "path") == nil then
        return source_figure(el, entry)
      end
      return render_figure(entry)
    end,
  })
end
