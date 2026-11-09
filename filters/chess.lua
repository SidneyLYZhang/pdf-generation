-- Chess fences.  `fen` / `chess` / `pgn` become captioned diagrams (staunton's
-- `diagram` already returns a figure, so numbering and `@fig:` work), and
-- `notation` becomes a move list.  The build script validates every option; this
-- file only translates them into Typst arguments.
--
-- `at:` needs a parsed game, not raw PGN text, hence `st-game(...)`.

local LANGS = { fen = "diagram", chess = "diagram", pgn = "diagram", notation = "notation" }
local DIAGRAM_FLAGS = { "flip", "labels", "check" }
local NOTATION_FLAGS = { "figurine", "variations", "nags", "comments", "move-numbers" }

local function typst_string(value)
  local escaped = value
    :gsub("\\", "\\\\")
    :gsub('"', '\\"')
    :gsub("\r", "\\r")
    :gsub("\n", "\\n")
  return '"' .. escaped .. '"'
end

local function attr(el, name)
  local value = el.attributes[name]
  if value == nil or value == "" then
    return nil
  end
  return value
end

local function typst_bool(value)
  local lowered = value:lower()
  if lowered == "true" or lowered == "yes" then
    return "true"
  end
  return "false"
end

-- `"e5,d4"` -> `("e5", "d4",)`, `"f3e5,f1c4"` -> `(("f3", "e5"), ("f1", "c4"),)`.
-- The build script validates every square, so no escaping is needed here.
local function typst_list(value, as_pairs)
  local items = {}
  for item in value:gmatch("[^,]+") do
    if as_pairs then
      items[#items + 1] = '("' .. item:sub(1, 2) .. '", "' .. item:sub(3, 4) .. '"),'
    else
      items[#items + 1] = '"' .. item .. '",'
    end
  end
  return "(" .. table.concat(items) .. ")"
end

-- staunton's `last-move` is a style (none / "arrow" / "squares"), not a switch.
local function last_move_argument(value)
  local lowered = value:lower()
  if lowered == "none" then
    return "last-move: none"
  end
  return 'last-move: "' .. lowered .. '"'
end

local function source_argument(el)
  if el.classes[1] == "pgn" then
    return "st-game(" .. typst_string(el.text) .. ")"
  end
  return typst_string(el.text)
end

function Pandoc(doc)
  local mode = doc.meta["pdfgen-chess"]
  if mode == nil then
    return doc
  end
  local chinese = pandoc.utils.stringify(mode):sub(1, 2) == "zh"
  return doc:walk({
    CodeBlock = function(el)
      local callee = LANGS[el.classes[1]]
      if callee == nil then
        return nil
      end
      local args = {}
      if callee == "notation" then
        -- Comments, NAGs and variations only exist on a parsed game, so the
        -- source always goes through `st-game`.
        args[#args + 1] = "st-game(" .. typst_string(el.text) .. ")"
        for _, flag in ipairs(NOTATION_FLAGS) do
          local value = attr(el, flag)
          if value ~= nil then
            args[#args + 1] = flag .. ": " .. typst_bool(value)
          end
        end
        return pandoc.RawBlock("typst", "#st-notation(" .. table.concat(args, ", ") .. ")")
      end

      args[#args + 1] = source_argument(el)
      local at = attr(el, "at")
      if at ~= nil then
        args[#args + 1] = "at: " .. typst_string(at)
      end
      local size = attr(el, "size")
      if size ~= nil then
        args[#args + 1] = "size: " .. size
      end
      for _, flag in ipairs(DIAGRAM_FLAGS) do
        local value = attr(el, flag)
        if value ~= nil then
          args[#args + 1] = flag .. ": " .. typst_bool(value)
        end
      end
      local last_move = attr(el, "last-move")
      if last_move ~= nil then
        args[#args + 1] = last_move_argument(last_move)
      end
      local theme = attr(el, "theme")
      if theme ~= nil then
        args[#args + 1] = 'color-theme: st-color-theme(base: "' .. theme:lower() .. '")'
      end
      local arrows = attr(el, "arrows")
      if arrows ~= nil then
        args[#args + 1] = "arrows: " .. typst_list(arrows, true)
      end
      local highlight = attr(el, "highlight")
      if highlight ~= nil then
        args[#args + 1] = "highlight: " .. typst_list(highlight, false)
      end
      local caption = attr(el, "caption")
      if caption ~= nil then
        args[#args + 1] = "caption: [#text(" .. typst_string(caption) .. ")]"
      end
      if chinese then
        -- Typst numbers figures per kind, so a board and a photo would both be
        -- "图 1".  A distinct prefix keeps the two sequences unambiguous.
        args[#args + 1] = "supplement: [棋图]"
      end
      local call = "#st-diagram(" .. table.concat(args, ", ") .. ")"
      local label = el.identifier
      if label ~= nil and label ~= "" then
        call = call .. "<" .. label .. ">"
      end
      return pandoc.RawBlock("typst", call)
    end,
  })
end
