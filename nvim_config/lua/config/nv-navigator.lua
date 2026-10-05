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
