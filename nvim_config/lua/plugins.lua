--:PackerSync after adding packages or if you want to update them

-- Consider switching to lazy: https://github.com/folke/lazy.nvim

local ensure_packer = function()
	local fn = vim.fn
	local install_path = fn.stdpath("data") .. "/site/pack/packer/start/packer.nvim"
	if fn.empty(fn.glob(install_path)) > 0 then
		fn.system({ "git", "clone", "--depth", "1", "https://github.com/wbthomason/packer.nvim", install_path })
		vim.cmd([[packadd packer.nvim]])
		return true
	end
	return false
end

local packer_bootstrap = ensure_packer()

require("packer").startup(function(use)
	use("wbthomason/packer.nvim")

	-- Directory / searching plugins
	-- For directory navigation
	use("tpope/vim-vinegar")
	-- Fuzzy searching
	use({
		"junegunn/fzf",
		run = function()
			vim.fn["fzf#install"](0)
		end,
	})

	use({
		"junegunn/fzf.vim",
		config = function()
			require("config.fzf").setup()
		end,
	})

	-- LSP plugins
	use({
		"neovim/nvim-lspconfig",
		config = function()
			require("config.lsp.init").setup()
		end,
	})
	use("L3MON4D3/LuaSnip")
	use("saadparwaiz1/cmp_luasnip")
	use("hrsh7th/cmp-nvim-lsp")
	use({
		"hrsh7th/nvim-cmp",
		config = function()
			require("config.cmp").setup()
		end,
	})

	use({
		"williamboman/mason.nvim",
		config = function()
			require("config.mason").setup()
		end,
	})

	use("williamboman/mason-lspconfig.nvim", "neovim/nvim-lspconfig")

	use({
		"/jose-elias-alvarez/null-ls.nvim",
		config = function()
			require("config.null_ls").setup()
		end,
	})

	-- Gives diagnostics, pretty popups for goto definition/references/type
	use({
		"eric-qian-d/lspsaga.nvim",
		opt = true,
		branch = "main",
		event = "LspAttach",
		config = function()
			require("config/lspsaga").setup()
		end,
		requires = {
			{ "nvim-tree/nvim-web-devicons" },
			--Please make sure you install markdown and markdown_inline parser
			{ "nvim-treesitter/nvim-treesitter" },
		},
	})

	-- Editing plugins
	use({
		"windwp/nvim-autopairs",
		config = function()
			require("nvim-autopairs").setup()
		end,
	})
	-- Navigation
	use({
		"ggandor/leap.nvim",
		requires = { "tpope/vim-repeat", opt = true },
		keys = { "s", "S" },
		config = function()
			require("config/leap").setup()
		end,
	})
	-- Initialize  this after hop so that "<leader>s" in visual mode does surround
	use({
		"kylechui/nvim-surround",
		config = function()
			require("nvim-surround").setup({
				keymaps = {
					visual = "<leader>s",
				},
			})
		end,
	})

	use({
		"numToStr/Comment.nvim",
		config = function()
			require("Comment").setup({
				mappings = {
					basic = true,
					extra = false,
				},
				toggler = {
					line = "<leader>gl",
					block = "<leader>gb",
				},
				opleader = {
					line = "<leader>gl",
					block = "<leader>gb",
				},
			})
		end,
	})

	-- Git plugins

	-- Enables using git commands in vim
	use("tpope/vim-fugitive")
	-- For showing changes in the lefthand side
	use({
		"lewis6991/gitsigns.nvim",
		config = function()
			require("gitsigns").setup({
				current_line_blame = true,
			})
		end,
	})
	-- For opening a file in github - use :OpenInGHFile
	use("almo7aya/openingh.nvim")

	-- Visual plugins

	-- Editor 'theme'
	use({
		"navarasu/onedark.nvim",
		config = function()
			require("config.onedark").setup()
		end,
	})
	-- Editor status line
	-- Initializing lualine has to come after onedark in order for proper UI to take effect
	use({
		"nvim-lualine/lualine.nvim",
		requires = { "kyazdani42/nvim-web-devicons", opt = true },
		config = function()
			require("config.lualine").setup()
		end,
	})
	-- Shows todo comments etc
	use({
		"folke/todo-comments.nvim",
		requires = "nvim-lua/plenary.nvim",
		config = function()
			require("todo-comments").setup()
		end,
	})
	-- For text coloring
	use({
		"nvim-treesitter/nvim-treesitter",
		run = ":TSUpdate all",
		config = function()
			require("config.treesitter").setup()
		end,
	})

	-- Automatically set up your configuration after cloning packer.nvim
	-- Put this at the end after all plugins
	-- On update, need to run :PackerSync
	if packer_bootstrap then
		require("packer").sync()
	end
end)

vim.cmd([[
  augroup packer_user_config
    autocmd!
    autocmd BufWritePost plugins.lua source <afile> | PackerCompile
  augroup end
]])
