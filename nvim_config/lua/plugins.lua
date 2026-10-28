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
    {
        "tpope/vim-vinegar",
        cond = not vim.g.vscode,
    },
    -- Fuzzy searching
    {
        "junegunn/fzf",
        build = function()
            vim.fn["fzf#install"](0)
        end,
        cond = not vim.g.vscode,
    },
    -- For local plugin dev
    {
        "folke/neodev.nvim",
        config = function()
            require("config.neodev").setup()
        end,
        cond = not vim.g.vscode,
    },

    -- LSP plugins
    {
        "williamboman/mason.nvim",
        config = function()
            require("config.mason").setup()
        end,
        cond = not vim.g.vscode,
    },
    {
        "williamboman/mason-lspconfig.nvim",
        dependencies = {
            "williamboman/mason.nvim",
        },
        config = function()
            require("config.mason-lsp").setup()
        end,
        cond = not vim.g.vscode,
    },
    {
        "neovim/nvim-lspconfig",
        config = function()
            require("config.lsp.init").setup()
        end,
        cond = not vim.g.vscode,
    },
    {
        "L3MON4D3/LuaSnip",
        -- follow latest release.
        version = "v2.*", -- Replace <CurrentMajor> by the latest released major (first number of latest release)
        -- install jsregexp (optional!).
        build = "make install_jsregexp",
        cond = not vim.g.vscode,
    },
    {
        "saadparwaiz1/cmp_luasnip",
        cond = not vim.g.vscode,
    },
    {
        "hrsh7th/cmp-nvim-lsp",
        cond = not vim.g.vscode,
    },
    {
        "hrsh7th/nvim-cmp",
        config = function()
            require("config.cmp").setup()
        end,
        cond = not vim.g.vscode,
    },
    {

        "neovim/nvim-lspconfig",
        cond = not vim.g.vscode,
    },
    {
        "nvimtools/none-ls.nvim",
        dependencies = {
            "nvimtools/none-ls-extras.nvim",
        },
        config = function()
            require("config.null_ls").setup()
        end,
        cond = not vim.g.vscode,
    },
    {
        "jay-babu/mason-null-ls.nvim", -- Use null-ls as the SSOT for plugins
        event = { "BufReadPre", "BufNewFile" },
        dependencies = {
            "williamboman/mason.nvim",
        },
        config = function()
            require("config.mason-null").setup()
        end,
        cond = not vim.g.vscode,
    },

    {
        dir = vim.fn.expand("~/nv-navigator"),
        name = "nv-navigator",
        event = "LspAttach",
        cmd = { "NvNavigatorFiles", "NvNavigatorGrep", "NvNavigatorGitFiles", "NvNavigatorBuffers" },
        keys = {
            { "<leader>a", "<cmd>NvNavigatorGrep<CR>", desc = "Search text" },
            { "<leader>z", "<cmd>NvNavigatorFiles<CR>", desc = "Search files" },
            { "<leader>t", "<cmd>NvNavigatorGitFiles<CR>", desc = "Search Git files" },
            { ";", "<cmd>NvNavigatorBuffers<CR>", desc = "Search buffers" },
        },
        init = function()
            -- Let Lazy apply the configured keymaps instead of the plugin bootstrap defaults.
            vim.g.loaded_nv_navigator = 1
        end,
        config = function()
            require("config.nv-navigator").setup()
        end,
        dependencies = {
            { "ibhagwan/fzf-lua" },
        },
        cond = not vim.g.vscode,
    },

    -- Editing plugins
    {
        "windwp/nvim-autopairs",
        config = function()
            require("nvim-autopairs").setup()
        end,
        cond = not vim.g.vscode,
    },
    {
        "windwp/nvim-ts-autotag",
        config = function()
            require("nvim-ts-autotag").setup()
        end,
        cond = not vim.g.vscode,
    },
    {
        "github/copilot.vim",
        enabled = false,
        cond = not vim.g.vscode,
    },
    -- Navigation
    {
        url = "https://codeberg.org/andyg/leap.nvim",
        dependencies = { "tpope/vim-repeat", lazy = true },
        lazy = false,
        config = function()
            require("config/leap").setup()
        end,
    },
    -- Initialize  this after hop so that "<leader>s" in visual mode does surround
    {
        "kylechui/nvim-surround",
        config = function()
            require("nvim-surround").setup({})
            vim.keymap.set("x", "<leader>s", "<Plug>(nvim-surround-visual)", { remap = true })
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
        cond = not vim.g.vscode,
    },

    -- Render Markdown with Mermaid and PlantUML diagrams inside Neovim.
    {
        "delphinus/md-render.nvim",
        ft = "markdown",
        cmd = "MdRender",
        keys = {
            { "<leader>mp", "<cmd>MdRender<CR>", desc = "Markdown preview" },
            { "<leader>mt", "<cmd>MdRender tab<CR>", desc = "Markdown preview in tab" },
            { "<leader>ms", "<cmd>vertical MdRender split<CR>", desc = "Markdown preview in split" },
        },
        cond = not vim.g.vscode,
    },

    -- Git plugins

    {
        "ericdqian/nvim-review",
        branch = "eq/feat/neovim-diff-viewer",
        dev = true,
        cmd = { "Review", "ReviewClose", "ReviewRefresh" },
        cond = not vim.g.vscode,
    },

    -- Enables using git commands in vim
    {
        "tpope/vim-fugitive",
        cond = not vim.g.vscode,
    },
    -- For showing changes in the lefthand side
    {
        "lewis6991/gitsigns.nvim",
        config = function()
            require("gitsigns").setup({
                current_line_blame = true,
            })
        end,
        cond = not vim.g.vscode,
    },
    -- For opening a file in github - use :OpenInGHFile
    {
        "almo7aya/openingh.nvim",
        config = function()
            vim.api.nvim_set_keymap(
                "n",
                "<leader>gh",
                "<cmd>OpenInGHFileLines<CR>",
                { noremap = true, silent = true }
            )
        end,
    },

    -- Visual plugins
    {
        "MeanderingProgrammer/render-markdown.nvim",
        ft = { "markdown" },
        cmd = { "RenderMarkdown" },
        dependencies = {
            "nvim-treesitter/nvim-treesitter",
            "nvim-tree/nvim-web-devicons",
        },
        opts = {
            anti_conceal = { enabled = false },
            custom_handlers = {
                markdown_inline = {
                    extends = true,
                    parse = require("config.markdown_links").parse,
                },
            },
            win_options = {
                concealcursor = { rendered = "nc" },
            },
        },
        keys = {
            { "<leader>mr", "<cmd>RenderMarkdown buf_toggle<CR>", desc = "Toggle Markdown rendering" },
        },
        cond = not vim.g.vscode,
    },
    -- Editor 'theme'
    {
        "navarasu/onedark.nvim",
        config = function()
            require("config.onedark").setup()
        end,
        cond = not vim.g.vscode,
    },
    -- Editor status line
    -- Initializing lualine has to come after onedark in order for proper UI to take effect
    {
        "nvim-lualine/lualine.nvim",
        dependencies = { "kyazdani42/nvim-web-devicons", lazy = true },
        config = function()
            require("config.lualine").setup()
        end,
        cond = not vim.g.vscode,
    },
    -- Shows todo comments etc
    {
        "folke/todo-comments.nvim",
        dependencies = "nvim-lua/plenary.nvim",
        config = function()
            require("todo-comments").setup()
        end,
        cond = not vim.g.vscode,
    },
    -- For text coloring
    {
        "nvim-treesitter/nvim-treesitter",
        branch = "main",
        build = ":TSUpdate",
        config = function()
            require("config.treesitter").setup()
        end,
        cond = not vim.g.vscode,
    },
    -- -- Custom plugin
    -- {
    -- 	dir = "~/simple-custom-nvim-plugin",
    -- },
}, {
    dev = {
        path = "~",
        fallback = true,
    },
})
