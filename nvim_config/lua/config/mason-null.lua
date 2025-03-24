local M = {}

function M.setup()
    require("mason-null-ls").setup({
        ensure_installed = nil,
        automatic_installation = true,
    })
end

return M
