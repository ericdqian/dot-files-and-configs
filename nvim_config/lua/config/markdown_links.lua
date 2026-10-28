local M = {}

local destination_highlight

function M.parse(context)
    local link_query = vim.treesitter.query.parse("markdown_inline", [[
        (inline_link
            (link_text) @text
            (link_destination) @destination) @link
    ]])
    local link_marks = {}
    for _, link_match in link_query:iter_matches(context.root, context.buf) do
        local link_text_node = link_match[1][1]
        local destination_node = link_match[2][1]
        local destination_text = vim.treesitter.get_node_text(destination_node, context.buf)
        local highlight_group = destination_highlight(
            destination_text,
            vim.api.nvim_buf_get_name(context.buf)
        )
        if highlight_group then
            local start_row, start_col, end_row, end_col = link_text_node:range()
            link_marks[#link_marks + 1] = {
                conceal = false,
                start_row = start_row,
                start_col = start_col,
                opts = {
                    end_row = end_row,
                    end_col = end_col,
                    hl_group = highlight_group,
                    priority = 1100,
                },
            }
        end
    end
    return link_marks
end

function destination_highlight(destination_text, source_path)
    local destination_path = destination_text:gsub("^<(.*)>$", "%1")
    if destination_path:match("^[%a][%w+.-]*:") then
        if not destination_path:match("^file://") then
            return nil
        end
        destination_path = destination_path:sub(8)
    elseif destination_path:sub(1, 2) == "//" then
        return nil
    end
    destination_path = destination_path:match("^[^#?]*"):gsub("%%(%x%x)", function(hex_byte)
        return string.char(tonumber(hex_byte, 16))
    end)
    if destination_path:sub(1, 1) ~= "/" then
        destination_path = vim.fs.joinpath(vim.fs.dirname(source_path), destination_path)
    end
    destination_path = vim.fs.normalize(destination_path)
    local extension = destination_path:match("%.([^./]+)$")
    if not extension then
        return nil
    end
    extension = extension:lower()
    if extension == "md" or extension == "markdown" then
        if ("/" .. destination_path):find("/concepts/", 1, true) then
            return "RenderMarkdownConceptLink"
        end
        return nil
    end
    local source_extensions = {
        "c", "cc", "cpp", "cs", "css", "ex", "exs", "go", "h", "hpp", "html",
        "java", "js", "jsx", "kt", "lua", "mjs", "php", "py", "rb", "rs",
        "scala", "sh", "sql", "swift", "svelte", "ts", "tsx", "vue", "zsh",
    }
    if vim.list_contains(source_extensions, extension) then
        return "RenderMarkdownCodeLink"
    end
end

return M
