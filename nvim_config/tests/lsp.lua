-- Run with the installed config: nvim --headless -i NONE -c 'luafile nvim_config/tests/lsp.lua'
-- Scheduling lets Neovim finish startup before file-change checks run.
vim.schedule(function()
    local ok, test_error = pcall(function()
        local test_directory = vim.fn.tempname()
        vim.fn.mkdir(test_directory, "p")
        vim.fn.writefile({ "{}" }, test_directory .. "/package-lock.json")
        vim.fn.writefile(
            { '{"compilerOptions":{"strict":true},"include":["*.ts"]}' },
            test_directory .. "/tsconfig.json"
        )
        vim.fn.writefile({ "export const greeting: string = 42;" }, test_directory .. "/main.ts")
        local started = vim.uv.hrtime()
        vim.cmd.edit(test_directory .. "/main.ts")
        assert(vim.wait(20000, function()
            return #vim.lsp.get_clients({ bufnr = 0, name = "ts_ls" }) > 0
        end, 20))
        print("ATTACH_MS", (vim.uv.hrtime() - started) / 1e6)
        local buffer = vim.api.nvim_get_current_buf()
        assert(
            vim.wait(20000, function()
                return #vim.diagnostic.get(buffer) > 0
            end, 50),
            "initial diagnostics missing"
        )
        print("DIAGNOSTICS_MS", (vim.uv.hrtime() - started) / 1e6)
        vim.fn.writefile(
            { 'export const greeting: string = "external agent edit";' },
            vim.api.nvim_buf_get_name(buffer)
        )
        vim.api.nvim_exec_autocmds("CursorHold", {})
        assert(
            vim.wait(3000, function()
                return vim.api
                    .nvim_buf_get_lines(buffer, 0, 1, false)[1]
                    :find("external agent edit") ~= nil
            end, 20),
            "agent edit not reloaded"
        )
        assert(
            vim.wait(15000, function()
                return #vim.diagnostic.get(buffer) == 0
            end, 50),
            "LSP kept stale diagnostics"
        )
        print("EXTERNAL_EDIT_AND_LSP_REFRESH_PASS")
        vim.api.nvim_buf_set_lines(
            buffer,
            0,
            1,
            false,
            { 'export const greeting = "unsaved edit";' }
        )
        vim.fn.writefile(
            { 'export const greeting = "conflicting agent edit";' },
            vim.api.nvim_buf_get_name(buffer)
        )
        vim.api.nvim_exec_autocmds("CursorHold", {})
        vim.wait(200)
        assert(
            vim.api.nvim_buf_get_lines(buffer, 0, 1, false)[1]:find("unsaved edit"),
            "unsaved edits overwritten"
        )
        print("UNSAVED_EDIT_PRESERVED_PASS")
        vim.bo.modified = false
        vim.cmd.enew()
        local definition = require("lspsaga.definition")
        vim.cmd("Lspsaga peek_definition")
        assert(not definition.pending_request, "unsupported definition left lock set")
        print("UNSUPPORTED_DEFINITION_PASS")
        local unsupported_action = require("lspsaga.codeaction")
        unsupported_action:code_action()
        assert(not unsupported_action.pending_request, "unsupported code action left lock set")
        print("UNSUPPORTED_CODE_ACTION_PASS")
        vim.api.nvim_set_current_buf(buffer)
        local action = require("lspsaga.codeaction")
        for _, options in ipairs({ {}, { context = {} }, { only = { "quickfix" } } }) do
            action:code_action(options)
            assert(
                vim.wait(5000, function()
                    return not action.pending_request
                end, 20),
                "action remained pending"
            )
            action:close_action_window()
            vim.api.nvim_set_current_buf(buffer)
        end
        print("REPEATED_CODE_ACTION_PASS")
        local original_send_request = action.send_request
        action.send_request = function()
            error("injected request failure")
        end
        local ok = pcall(action.code_action, action)
        assert(not ok and not action.pending_request, "error left action lock set")
        action.send_request = original_send_request
        print("ERROR_RECOVERY_PASS")
        vim.fn.delete(test_directory, "rf")
    end)
    if not ok then
        print(test_error)
        vim.cmd("cq")
    else
        vim.cmd("qa!")
    end
end)
