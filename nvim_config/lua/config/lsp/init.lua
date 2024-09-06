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
		"clangd", -- brew install llvm if not using Mason
		"rust_analyzer", --brew install rust-analyzer if not using Mason
		"lua_ls",
		"tflint",
		"bashls",
		-- "terraformls",
	}
	for _, lsp in ipairs(servers) do
		lspconfig[lsp].setup({
			on_attach = custom_attach,
			capabilities = capabilities,
		})
	end

	lspconfig.lua_ls.setup({ -- brew install lua-language-server if not using Mason
		on_attach = custom_attach,
		capabilities = capabilities,
		settings = {
			Lua = {
				runtime = {
					-- Tell the language server which version of Lua you're using (most likely LuaJIT in the case of Neovim)
					version = "LuaJIT",
				},
				diagnostics = {
					-- Get the language server to recognize the `vim` global
					globals = { "vim" },
				},
				workspace = {
					-- Make the server aware of Neovim runtime files
					library = vim.api.nvim_get_runtime_file("", true),
				},
				-- Do not send telemetry data containing a randomized but unique identifier
				telemetry = {
					enable = false,
				},
			},
		},
	})

	lspconfig.pyright.setup({
		on_attach = custom_attach,
		capabilities = capabilities,
		settings = {
			python = {
				pythonPath = vim.fn.exepath("python"), -- Forces pyright to use the same python as the activated venv instead of potentially `python3`
			},
		},
	})

	--[[ yarn install -g tsserver
	tsserver initializationOptions:
	https://github.com/typescript-language-server/typescript-language-server/blob/master/docs/configuration.md/#workspacedidchangeconfiguration
	tsserver workspace/didChangeconfiguration:
	https://github.com/typescript-language-server/typescript-language-server/blob/master/docs/configuration.md#workspacedidchangeconfiguration ]]
	lspconfig.ts_ls.setup({
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
