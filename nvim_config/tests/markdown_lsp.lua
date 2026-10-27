-- Run from the repo root: nvim --headless -u NONE -i NONE -l nvim_config/tests/markdown_lsp.lua
vim.opt.runtimepath:prepend(vim.fn.getcwd() .. "/nvim_config")
vim.opt.runtimepath:append(vim.fn.stdpath("data") .. "/site")
vim.opt.runtimepath:append(vim.fn.stdpath("data") .. "/lazy/nvim-treesitter")
vim.opt.runtimepath:append(vim.fn.stdpath("data") .. "/lazy/nv-navigator")
package.preload.cmp_nvim_lsp = function()
    return {
        default_capabilities = function()
            return {}
        end,
    }
end
require("config.lsp.init").setup()

local fixture_root = vim.fn.resolve(vim.fn.tempname())
local client_id
local function write_fixture(relative_path, lines)
    local fixture_path = vim.fs.joinpath(fixture_root, relative_path)
    vim.fn.mkdir(vim.fs.dirname(fixture_path), "p")
    vim.fn.writefile(lines, fixture_path)
    return fixture_path
end

local succeeded, failure = pcall(function()
    local target_path = write_fixture("runs/target with space.md", {
        "# Target",
        "",
        "## Useful heading!",
        "",
        "## Useful heading!",
        "",
        "Setext heading",
        "---",
    })
    local source_path = write_fixture("docs/source.md", {
        "# Links",
        "[absolute](" .. target_path:gsub(" ", "%%20") .. ")",
        "[relative](../runs/target%20with%20space.md)",
        "[file URI](" .. vim.uri_from_fname(target_path) .. ")",
        "[heading](../runs/target%20with%20space.md#useful-heading)",
        "[duplicate](../runs/target%20with%20space.md#useful-heading-1)",
        "[setext](../runs/target%20with%20space.md#setext-heading)",
        "[line](../outside.ts#L2)",
        "[angle](<../runs/target with space.md>)",
        "[site](https://example.com)",
        "[missing](../runs/missing.md)",
        "`[code](../runs/target%20with%20space.md)`",
        "[ordinary](../indexed.md)",
        "💡 [unicode prefix](../runs/target%20with%20space.md)",
        "[bad heading](../runs/target%20with%20space.md#not-a-heading)",
    })
    local indexed_path = write_fixture("indexed.md", { "# Indexed" })
    local typescript_path = write_fixture("outside.ts", { "const first = 1;", "const second = 2;" })
    write_fixture(".gitignore", { "runs/" })
    write_fixture(".marksman.toml", {})
    local marksman_path = vim.fn.stdpath("data") .. "/mason/bin/marksman"
    assert(
        vim.fn.executable(marksman_path) == 1,
        "Install Marksman before running this integration check"
    )
    vim.cmd.edit(source_path)
    vim.bo.filetype = "markdown"
    local source_bufnr = vim.api.nvim_get_current_buf()
    client_id = vim.lsp.start({
        name = "marksman",
        cmd = { marksman_path, "server" },
        root_dir = fixture_root,
        on_attach = vim.lsp.config.marksman.on_attach,
    })
    assert(
        vim.wait(5000, function()
            local client = vim.lsp.get_client_by_id(client_id)
            return client and client._local_link_definitions
        end),
        "Marksman failed to attach"
    )
    local client = vim.lsp.get_client_by_id(client_id)
    local wrapped_request = client.request
    require("config.lsp.markdown").attach_definition_fallback(client)
    assert(client.request == wrapped_request, "attached the fallback twice")
    local other_client = { name = "ts_ls", request = function() end }
    local original_other_request = other_client.request
    require("config.lsp.markdown").attach_definition_fallback(other_client)
    assert(other_client.request == original_other_request, "changed a different LSP")

    local request_error = { code = -32800, message = "Request cancelled" }
    local response_context = { client_id = client_id }
    local error_client = {
        name = "marksman",
        offset_encoding = "utf-16",
        handlers = {},
        request = function(_, _, _, handler)
            handler(request_error, nil, response_context)
            return true, 42
        end,
    }
    require("config.lsp.markdown").attach_definition_fallback(error_client)
    local preserved_error
    local request_succeeded, request_id = error_client:request("textDocument/definition", {
        textDocument = { uri = vim.uri_from_fname(source_path) },
        position = { line = 1, character = 2 },
    }, function(err, result, context)
        preserved_error = err
        assert(result == nil and context == response_context, "changed error callback arguments")
    end, source_bufnr)
    assert(preserved_error == request_error, "replaced cancellation with a fallback")
    assert(request_succeeded and request_id == 42, "changed request return values")

    local untouched_method
    local hover_client = {
        name = "marksman",
        request = function(_, method, _, handler)
            untouched_method = method
            handler(nil, "hover result")
        end,
    }
    require("config.lsp.markdown").attach_definition_fallback(hover_client)
    hover_client:request("textDocument/hover", {}, function(_, result)
        assert(result == "hover result", "changed non-definition callback")
    end)
    assert(untouched_method == "textDocument/hover")

    local function definition_at(source_line, byte_column)
        vim.api.nvim_set_current_buf(source_bufnr)
        vim.api.nvim_win_set_cursor(0, { source_line, byte_column or 2 })
        local results
        vim.lsp.buf_request_all(
            source_bufnr,
            "textDocument/definition",
            vim.lsp.util.make_position_params(0, client.offset_encoding),
            function(responses)
                results = responses
            end
        )
        assert(
            vim.wait(5000, function()
                return results ~= nil
            end),
            "definition response timed out"
        )
        assert(not results[client_id].err, vim.inspect(results[client_id].err))
        local locations = results[client_id].result
        if locations == nil or vim.tbl_isempty(locations) then
            return nil
        end
        return locations.uri and locations or locations[1]
    end

    for _, source_line in ipairs({ 2, 3, 4, 9, 14 }) do
        local location = definition_at(source_line, source_line == 14 and 8 or 2)
        assert(
            location and vim.uri_to_fname(location.uri) == target_path,
            "link failed on line "
                .. source_line
                .. ": "
                .. vim.inspect(location)
                .. " expected "
                .. target_path
        )
    end
    local destination_location = definition_at(2, 15)
    assert(destination_location and vim.uri_to_fname(destination_location.uri) == target_path)
    for source_line, expected_line in pairs({ [5] = 2, [6] = 4, [7] = 6 }) do
        local location = definition_at(source_line)
        assert(
            location and location.range.start.line == expected_line,
            "heading failed on line " .. source_line
        )
    end
    local line_location = definition_at(8)
    assert(line_location and vim.uri_to_fname(line_location.uri) == typescript_path)
    assert(line_location.range.start.line == 1, "source line anchor lost")
    for _, source_line in ipairs({ 10, 11, 12, 15 }) do
        assert(definition_at(source_line) == nil, "invented definition on line " .. source_line)
    end
    assert(
        vim.uri_to_fname(definition_at(13).uri) == indexed_path,
        "normal Marksman definition changed"
    )

    -- A request uses its own source and position, even if focus changes before its callback.
    local pending_location
    local source_params = {
        textDocument = { uri = vim.uri_from_fname(source_path) },
        position = { line = 2, character = 2 },
    }
    client:request("textDocument/definition", source_params, function(err, locations)
        assert(not err)
        pending_location = locations[1]
    end, source_bufnr)
    vim.cmd.enew()
    assert(vim.wait(5000, function()
        return pending_location ~= nil
    end))
    assert(vim.uri_to_fname(pending_location.uri) == target_path, "resolved against focused buffer")

    -- The actual gd entry point supplies a callback and must still receive a Location.
    require("nv-navigator.config").setup({})
    vim.api.nvim_set_current_buf(source_bufnr)
    vim.api.nvim_win_set_cursor(0, { 2, 2 })
    local source_window = vim.api.nvim_get_current_win()
    require("nv-navigator.lsp").definition()
    assert(
        vim.wait(5000, function()
            return vim.api.nvim_get_current_win() ~= source_window
        end),
        "gd did not open its preview"
    )
    assert(
        vim.api.nvim_buf_get_lines(0, 0, 1, false)[1] == "# Target",
        "gd previewed the wrong file"
    )
    local open_preview = vim.fn.maparg("<CR>", "n", false, true).callback
    assert(type(open_preview) == "function")
    open_preview()
    assert(vim.api.nvim_buf_get_name(0) == target_path, "preview open did not jump to target")
    local jump_list = vim.fn.getjumplist()[1]
    assert(
        vim.iter(jump_list):any(function(jump)
            return jump.bufnr == source_bufnr
        end),
        "source missing from jumplist"
    )
end)

if client_id then
    vim.lsp.get_client_by_id(client_id):stop(true)
end
vim.fn.delete(fixture_root, "rf")
assert(succeeded, failure)
print("Markdown definition fallback integration checks passed")
