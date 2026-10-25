local M = {}

function M.setup()
    require("nv-navigator").setup({
        picker = {
            fzf_opts = {
                keymap = {
                    fzf = {
                        ["ctrl-p"] = "up-match",
                        ["ctrl-n"] = "down-match",
                        ["alt-p"] = "prev-history",
                        ["alt-n"] = "next-history",
                    },
                },
            },
        },
        keymaps = {
            definition = "gd",
            type_definition = "gt",
            references = "gr",
            hover = "K",
            rename = "rn",
        },
    })

    vim.keymap.set("n", "gp", "<cmd>NvNavigatorDefinition<CR>", {
        desc = "Preview definition",
        silent = true,
    })

    -- End of nv-navigator configuration; native Neovim fallbacks follow.
    -- TODO: Add code actions, diagnostics, and call hierarchy support to nv-navigator.
    vim.keymap.set({ "n", "v" }, "<leader>ca", vim.lsp.buf.code_action, { desc = "Code action" })
    vim.keymap.set("n", "rN", vim.lsp.buf.rename, { desc = "Rename symbol in workspace" })
    vim.keymap.set("n", "<leader>sl", function()
        vim.diagnostic.open_float({ scope = "line" })
    end, { desc = "Line diagnostics" })
    vim.keymap.set("n", "<leader>sc", function()
        vim.diagnostic.open_float({ scope = "cursor" })
    end, { desc = "Cursor diagnostics" })
    vim.keymap.set("n", "<leader>sb", vim.diagnostic.setloclist, { desc = "Buffer diagnostics" })
    vim.keymap.set("n", "<leader>sw", vim.diagnostic.setqflist, { desc = "Workspace diagnostics" })
    for _, direction in ipairs({ { "[", -1 }, { "]", 1 } }) do
        for _, diagnostic_filter in ipairs({
            { "e" },
            { "g", vim.diagnostic.severity.ERROR },
            { "t", { max = vim.diagnostic.severity.WARN } },
        }) do
            vim.keymap.set("n", direction[1] .. diagnostic_filter[1], function()
                vim.diagnostic.jump({ count = direction[2], severity = diagnostic_filter[2], float = true })
            end, { desc = "Jump to diagnostic" })
        end
    end
    vim.keymap.set("n", "<leader>ci", vim.lsp.buf.incoming_calls, { desc = "Incoming calls" })
    vim.keymap.set("n", "<leader>co", vim.lsp.buf.outgoing_calls, { desc = "Outgoing calls" })
end

return M
