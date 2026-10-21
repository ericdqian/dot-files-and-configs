local M = {}

function M.setup()
    local use_navigator_lsp = (vim.env.NV_LSP_UI or "lspsaga") == "navigator"
    local navigator_keymaps = use_navigator_lsp
            and {
                definition = "gd",
                type_definition = "gt",
                references = "gr",
                hover = "K",
                code_action = "<leader>ca",
                rename = "rn",
            }
        or {}
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
        keymaps = navigator_keymaps,
    })

    if use_navigator_lsp then
        vim.keymap.set("n", "gp", "<cmd>NvNavigatorDefinition<CR>", {
            desc = "Preview definition",
            silent = true,
        })
    end
end

return M
