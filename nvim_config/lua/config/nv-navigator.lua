local M = {}

function M.setup()
    require("nv-navigator").setup({
        keymaps = {
            definition = "gd",
            type_definition = "gt",
            references = "gr",
            hover = "K",
            code_action = "<leader>ca",
            rename = "rn",
        },
    })

    vim.keymap.set("n", "gp", "<cmd>NvNavigatorDefinition<CR>", {
        desc = "Preview definition",
        silent = true,
    })
end

return M
