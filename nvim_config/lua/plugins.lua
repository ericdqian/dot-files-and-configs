local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
	vim.fn.system({
		"git",
		"clone",
		"--filter=blob:none",
		"https://github.com/folke/lazy.nvim.git",
		"--branch=stable", -- latest stable release
		lazypath,
	})
end
vim.opt.rtp:prepend(lazypath)

vim.g.mapleader = " "

require("lazy").setup({
	-- Directory / searching plugins
	-- For directory navigation
	"tpope/vim-vinegar",
	-- Fuzzy searching
	{
		"junegunn/fzf",
		build = function()
			vim.fn["fzf#install"](0)
		end,
	},

	{
		"junegunn/fzf.vim",
		config = function()
			require("config.fzf").setup()
		end,
	},
	-- For local plugin dev
	{
		"folke/neodev.nvim",
		config = function()
			require("config.neodev").setup()
		end,
	},

	-- LSP plugins
	{
		"williamboman/mason.nvim",
		config = function()
			require("config.mason").setup()
		end,
	},
	{
		"williamboman/mason-lspconfig.nvim",
		dependencies = {
			"williamboman/mason.nvim",
		},
		config = function()
			require("config.mason-lsp").setup()
		end,
	},
	{
		"neovim/nvim-lspconfig",
		config = function()
			require("config.lsp.init").setup()
		end,
	},
	{
		"jay-babu/mason-null-ls.nvim",
		event = { "BufReadPre", "BufNewFile" },
		dependencies = {
			"williamboman/mason.nvim",
		},
		config = function()
			require("config.mason-null")
		end,
	},
	{
		"L3MON4D3/LuaSnip",
		-- follow latest release.
		version = "v2.*", -- Replace <CurrentMajor> by the latest released major (first number of latest release)
		-- install jsregexp (optional!).
		build = "make install_jsregexp",
	},
	"saadparwaiz1/cmp_luasnip",
	"hrsh7th/cmp-nvim-lsp",
	{
		"hrsh7th/nvim-cmp",
		config = function()
			require("config.cmp").setup()
		end,
	},

	"neovim/nvim-lspconfig",

	{
		"/jose-elias-alvarez/null-ls.nvim",
		config = function()
			require("config.null_ls").setup()
		end,
	},

	-- Gives diagnostics, pretty popups for goto definition/references/type
	{
		"eric-qian-d/lspsaga.nvim",
		lazy = true,
		branch = "main",
		event = "LspAttach",
		config = function()
			require("config/lspsaga").setup()
		end,
		dependencies = {
			{ "nvim-tree/nvim-web-devicons" },
			--Please make sure you install markdown and markdown_inline parser
			{ "nvim-treesitter/nvim-treesitter" },
		},
	},

	-- Editing plugins
	{
		"windwp/nvim-autopairs",
		config = function()
			require("nvim-autopairs").setup()
		end,
	},
	{
		"windwp/nvim-ts-autotag",
		config = function()
			require("nvim-ts-autotag").setup()
		end,
	},
	-- Navigation
	{
		"ggandor/leap.nvim",
		dependencies = { "tpope/vim-repeat", lazy = true },
		keys = { "s", "S" },
		config = function()
			require("config/leap").setup()
		end,
	},
	-- Initialize  this after hop so that "<leader>s" in visual mode does surround
	{
		"kylechui/nvim-surround",
		config = function()
			require("nvim-surround").setup({
				keymaps = {
					visual = "<leader>s",
				},
			})
		end,
	},

	{
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
	},

	-- Git plugins

	-- Enables using git commands in vim
	"tpope/vim-fugitive",
	-- For showing changes in the lefthand side
	{
		"lewis6991/gitsigns.nvim",
		config = function()
			require("gitsigns").setup({
				current_line_blame = true,
			})
		end,
	},
	-- For opening a file in github - use :OpenInGHFile
	"almo7aya/openingh.nvim",

	-- Visual plugins

	-- Editor 'theme'
	{
		"navarasu/onedark.nvim",
		config = function()
			require("config.onedark").setup()
		end,
	},
	-- Editor status line
	-- Initializing lualine has to come after onedark in order for proper UI to take effect
	{
		"nvim-lualine/lualine.nvim",
		dependencies = { "kyazdani42/nvim-web-devicons", lazy = true },
		config = function()
			require("config.lualine").setup()
		end,
	},
	-- Shows todo comments etc
	{
		"folke/todo-comments.nvim",
		dependencies = "nvim-lua/plenary.nvim",
		config = function()
			require("todo-comments").setup()
		end,
	},
	-- For text coloring
	{
		"nvim-treesitter/nvim-treesitter",
		build = ":TSUpdate all",
		config = function()
			require("config.treesitter").setup()
		end,
	},
})
