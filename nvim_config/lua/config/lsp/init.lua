local M = {}

function M.setup()
	local capabilities = require("cmp_nvim_lsp").default_capabilities()

	local lspconfig = require("lspconfig")

	local custom_attach = function(client, bufnr)
		-- Do this to prevent lsp from overriding treesitter
		client.server_capabilities.semanticTokensProvider = nil
	end

	-- Custom lspconfig[lsp].setup: https://github.com/neovim/nvim-lspconfig/blob/master/doc/lspconfig.txt#L68
	-- Importantly, init_options corresponds to the LSP's initializationOptions configuration. initializationOptions is part of the LSP spec
	-- settings corresponds to the LSP's workspace/didChangeConfiguration configuration.

	-- Enable some language servers with the additional completion capabilities offered by nvim-cmp
	local servers = {
		"clangd", -- brew install llvm
		"rust_analyzer", --brew install rust-analyzer
		"pyright", -- yarn install -g pyright
		"lua_ls", -- brew install lua-language-server
		"tflint",
		-- "terraformls",
	}
	for _, lsp in ipairs(servers) do
		lspconfig[lsp].setup({
			on_attach = custom_attach,
			capabilities = capabilities,
		})
	end

	--[[ yarn install -g tsserver
	tsserver initializationOptions:
	https://github.com/typescript-language-server/typescript-language-server/blob/master/docs/configuration.md/#workspacedidchangeconfiguration
	tsserver workspace/didChangeconfiguration:
	https://github.com/typescript-language-server/typescript-language-server/blob/master/docs/configuration.md#workspacedidchangeconfiguration ]]
	lspconfig.tsserver.setup({
		init_options = {
			preferences = {
				importModuleSpecifierPreference = "non-relative",
			},
		},
	})

	vim.diagnostic.get(0, { update_in_insert = true }) -- Update diagnostics even while in insert mode
	vim.diagnostic.get(0, { virtual_text = false }) -- Don't show diagnostics with virtual text - real talk though: though what is virtual text?
end

return M
