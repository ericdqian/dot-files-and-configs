local M = {}

function M.setup()
    local capabilities = require("cmp_nvim_lsp").default_capabilities()

    local lspconfig = require("lspconfig")

    local custom_attach = function(client, bufnr)
        -- Do this to prevent lsp from overriding treesitter
        client.server_capabilities.semanticTokensProvider = nil
    end

    -- Enable some language servers with the additional completion capabilities offered by nvim-cmp
    local servers = { "clangd", "rust_analyzer", "pyright", "tsserver", "lua_ls" }
    for _, lsp in ipairs(servers) do
        lspconfig[lsp].setup({
            on_attach = custom_attach,
            capabilities = capabilities,
        })
    end

    vim.diagnostic.get(0, { update_in_insert = true }) -- Update diagnostics even while in insert mode
    vim.diagnostic.get(0, { virtual_text = false }) -- Don't show diagnostics with virtual text - real talk though: though what is virtual text?
end

return M
