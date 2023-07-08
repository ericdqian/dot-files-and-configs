local M = {}

function M.setup()
	require("mason").setup()
	require("mason-lspconfig").setup({
		ensure_installed = { "lua_ls", "rust_analyzer", "tsserver", "tailwindcss" },
	})
end

return M
