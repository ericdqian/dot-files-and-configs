local M = {}

local config_file_name = ".null_ls.nvim"

local function should_mount_python_source(source_name)
	local null_ls_utils = require("null-ls.utils")
	local root_path = null_ls_utils.root_pattern(config_file_name)(vim.api.nvim_buf_get_name(0))
	if root_path == nil then
		return false
	end
	local config_path = root_path .. "/" .. config_file_name
	local config_file = io.open(config_path, "r")
	if config_file == nil then
		return false
	end
	local raw_config_content = config_file:read("*a")
	local config_content = vim.fn.json_decode(raw_config_content)
	if config_content == nil then
		return false
	end
	if config_content["python"] == nil then
		print("Warning: no Python section in project's null_ls config. Check .null_ls in the project root")
		return false
	end
	local python_config_file_path = root_path .. "/" .. config_content["python"]

	local python_config_file = io.open(python_config_file_path, "r")
	if python_config_file == nil then
		return false
	end
	local python_config_file_raw_content = python_config_file:read("*a")
	return python_config_file_raw_content:find(source_name) ~= nil
end

function M.setup()
	local augroup = vim.api.nvim_create_augroup("LspFormatting", {})
	local null_ls = require("null-ls")
	null_ls.setup({
		-- you can reuse a shared lspconfig on_attach callback here
		on_attach = function(client, bufnr)
			if client.supports_method("textDocument/formatting") then
				vim.api.nvim_clear_autocmds({ group = augroup, buffer = bufnr })
				vim.api.nvim_create_autocmd("BufWritePre", {
					group = augroup,
					buffer = bufnr,
					callback = function()
						vim.lsp.buf.format({ bufnr = bufnr })
						-- vim.lsp.buf.formatting_sync()
					end,
				})
			end
		end,
		sources = {
			null_ls.builtins.formatting.stylua, --  brew install stylua
			null_ls.builtins.formatting.rustfmt, --  rustup component add rustfmt
			null_ls.builtins.formatting.prettier, -- installed on a per-project basis using: yarn add -D prettier
			-- can consider upgrading to prettierd: https://github.com/jose-elias-alvarez/null-ls.nvim/blob/main/doc/BUILTINS.md#prettierd
			null_ls.builtins.code_actions.eslint, --  installed on a per project basis
			null_ls.builtins.diagnostics.flake8.with({
				filetypes = { "python" },
				condition = function()
					return should_mount_python_source("flake8")
				end,
			}),
			null_ls.builtins.formatting.ruff.with({
				filetypes = { "python" },
				condition = function()
					return should_mount_python_source("ruff")
				end,
			}),
			null_ls.builtins.formatting.black.with({
				filetypes = { "python" },
				condition = function()
					return should_mount_python_source("black")
				end,
			}),
			null_ls.builtins.formatting.terraform_fmt,
		},
	})
end

return M
