local M = {}

local local_link_location
local link_at_position
local resolve_link_path
local fragment_position
local heading_slug

function M.attach_definition_fallback(client)
    if client.name ~= "marksman" or client._local_link_definitions then
        return
    end

    -- LSP clients are mutable handles. Wrapping this client's request also covers
    -- callers such as nv-navigator that supply their own response callbacks.
    local original_request = client.request
    client._local_link_definitions = true
    client.request = function(request_client, method, request_params, handler, bufnr)
        if method ~= "textDocument/definition" then
            return original_request(request_client, method, request_params, handler, bufnr)
        end

        -- Capture the source before the asynchronous response can change focus.
        local location_resolved, fallback_location =
            pcall(local_link_location, request_params, request_client.offset_encoding)
        local response_handler = handler
            or request_client.handlers[method]
            or vim.lsp.handlers[method]
        if not response_handler then
            return original_request(request_client, method, request_params, handler, bufnr)
        end
        return original_request(
            request_client,
            method,
            request_params,
            function(request_error, definition_result, context, config)
                if
                    not request_error
                    and location_resolved
                    and fallback_location
                    and (definition_result == nil or vim.tbl_isempty(definition_result))
                then
                    definition_result = { fallback_location }
                end
                return response_handler(request_error, definition_result, context, config)
            end,
            bufnr
        )
    end
end

function local_link_location(params, position_encoding)
    local source_bufnr = vim.uri_to_bufnr(params.textDocument.uri)
    if vim.bo[source_bufnr].filetype ~= "markdown" then
        return nil
    end
    local link_target = link_at_position(source_bufnr, params.position, position_encoding)
    if not link_target then
        return nil
    end
    local target_path, fragment =
        resolve_link_path(link_target, vim.api.nvim_buf_get_name(source_bufnr))
    if not target_path or vim.fn.filereadable(target_path) ~= 1 then
        return nil
    end
    local target_position = fragment_position(target_path, fragment)
    if not target_position then
        return nil
    end
    return {
        uri = vim.uri_from_fname(target_path),
        range = { start = target_position, ["end"] = target_position },
    }
end

function link_at_position(source_bufnr, position, position_encoding)
    local source_line =
        vim.api.nvim_buf_get_lines(source_bufnr, position.line, position.line + 1, false)[1]
    local byte_column = vim.str_byteindex(source_line, position_encoding, position.character, false)
    local parser = vim.treesitter.get_parser(source_bufnr, "markdown")
    parser:parse(true)
    local link_node = vim.treesitter.get_node({
        bufnr = source_bufnr,
        pos = { position.line, byte_column },
        ignore_injections = false,
    })
    while link_node and link_node:type() ~= "inline_link" do
        link_node = link_node:parent()
    end
    if link_node then
        for child_node in link_node:iter_children() do
            if child_node:type() == "link_destination" then
                return vim.treesitter.get_node_text(child_node, source_bufnr)
            end
        end
    end
end

function resolve_link_path(link_target, source_path)
    link_target = link_target:gsub("^<(.*)>$", "%1"):gsub("\\([%p])", "%1")
    local target_path, fragment = link_target:match("^([^#]*)#?(.*)$")
    if target_path:match("^[%a][%w+.-]*:") and not target_path:match("^file://") then
        return nil
    end
    if target_path:sub(1, 2) == "//" then
        return nil
    end
    if target_path:match("^file://") then
        target_path = vim.uri_to_fname(target_path)
    else
        target_path = target_path:gsub("%%(%x%x)", function(hex_byte)
            return string.char(tonumber(hex_byte, 16))
        end)
    end
    if target_path == "" then
        target_path = source_path
    elseif target_path:sub(1, 1) ~= "/" then
        target_path = vim.fs.joinpath(vim.fs.dirname(source_path), target_path)
    end
    return vim.fs.normalize(target_path), fragment
end

function fragment_position(target_path, fragment)
    if fragment == "" then
        return { line = 0, character = 0 }
    end
    local line_number = fragment:match("^L(%d+)$") or fragment:match("^L(%d+)%-L%d+$")
    if line_number then
        return { line = math.max(tonumber(line_number) - 1, 0), character = 0 }
    end
    if not target_path:match("%.md$") and not target_path:match("%.markdown$") then
        return nil
    end

    local target_text = table.concat(vim.fn.readfile(target_path), "\n") .. "\n"
    local parser = vim.treesitter.get_string_parser(target_text, "markdown")
    local headings =
        vim.treesitter.query.parse("markdown", "[(atx_heading) (setext_heading)] @heading")
    local heading_counts = {}
    for _, heading_node in headings:iter_captures(parser:parse()[1]:root(), target_text) do
        local heading_content = heading_node:field("heading_content")[1]
        if heading_content then
            local slug = heading_slug(vim.treesitter.get_node_text(heading_content, target_text))
            local duplicate_count = heading_counts[slug] or 0
            heading_counts[slug] = duplicate_count + 1
            if duplicate_count > 0 then
                slug = slug .. "-" .. duplicate_count
            end
            if slug == fragment then
                return { line = heading_node:start(), character = 0 }
            end
        end
    end
end

function heading_slug(heading_text)
    local lower_heading = vim.fn.tolower(heading_text)
    return vim.fn.substitute(lower_heading, "[^[:alnum:] _-]", "", "g"):gsub("%s", "-")
end

return M
