local M = {}

function M.setup()
    require("mason").setup()
    require("mason-lspconfig").setup({
        ensure_installed = {
            -- "lua_ls", --brew install lua-language-server
            -- "rust_analyzer", --brew install rust-analyzer
            "tsserver",
        },
    })
end

return M