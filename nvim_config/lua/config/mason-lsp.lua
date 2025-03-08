local M = {}

function M.setup()
	require("mason-lspconfig").setup({
		ensure_installed = {
			"lua_ls", --brew install lua-language-server
			"rust_analyzer", --brew install rust-analyzer
			"ts_ls", -- yarn global add tsserver
			"clangd",
			"pyright",
			"bashls", -- you may need to run `sudo nvim` in order to install this properly
			"terraformls",
			"tflint",
			"eslint",
		},
	})
end

return M
