local M = {}

function M.setup()
    require("mason-null-ls").setup({
        ensure_installed = { "stylua", "jq", "eslint" }
    })
end

return M
