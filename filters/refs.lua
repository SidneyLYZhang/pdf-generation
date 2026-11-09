-- Cross-references and citations.
--   Cite -> `@fig:` / `@tab:` / `@eq:` / `@sec:` become `#ref(<…>)`; every
--           other `@id` stays a citation for the bibliography.
--   Str  -> textual `\eqref{…}` / `\ref{…}` (our dialect has raw TeX off)
--           rewrite into the same `#ref`.
--
-- Runs before semantic.lua: its Div/Span handlers serialize their content into
-- Typst, and a Cite that left the AST as plain text can no longer be rewritten.

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
