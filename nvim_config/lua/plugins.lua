--:PackerSync after adding packages or if you want to update them

local ensure_packer = function()
    local fn = vim.fn
    local install_path = fn.stdpath('data') .. '/site/pack/packer/start/packer.nvim'
    if fn.empty(fn.glob(install_path)) > 0 then
        fn.system({ 'git', 'clone', '--depth', '1', 'https://github.com/wbthomason/packer.nvim', install_path })
        vim.cmd [[packadd packer.nvim]]
        return true
    end
    return false
end

local packer_bootstrap = ensure_packer()

require('packer').startup(function(use)
    use('wbthomason/packer.nvim')

    -- Directory / searching plugins
    -- For directory navigation
    use("tpope/vim-vinegar")
    -- Fuzzy searching
    use {
        'nvim-telescope/telescope.nvim', tag = '0.1.1',
        requires = { { 'nvim-lua/plenary.nvim' } },
        config = function()
            local builtin = require('telescope.builtin')
            vim.keymap.set('n', '<leader>z', builtin.find_files, {})
            vim.keymap.set('n', '<leader>a', builtin.live_grep, {})
            vim.keymap.set('n', ';', builtin.buffers, {})
            -- vim.keymap.set('n', '<leader>fh', builtin.help_tags, {})
            local telescope = require('telescope')
            local actions = require('telescope.actions')
            telescope.setup({
                defaults = {
                    mappings = {
                        i = {
                            ['<C-s>'] = actions.select_horizontal, -- Split horizontally with selection
                            ["<A-BS>"] = function() -- Overwrite alt+backspace in insert mode to do bulk delete
                                vim.cmd [[normal! bcw]]
                            end,
                        }
                    }
                },
                pickers = {
                    buffers = {
                        sort_mru = true,
                        -- sort_lastused = true, -- This is referring to where the selector is placed
                        ignore_current_buffer = false,
                    },
                    find_files = {
                        sort_mru = true,
                    }
                }
            })
        end
    }


    -- LSP plugins
    use('neovim/nvim-lspconfig')    -- Collection of common configurations for Nvim LSP
    use('hrsh7th/nvim-cmp')         -- Autocompletion plugin
    use('hrsh7th/cmp-nvim-lsp')     -- LSP source for nvim-cmp (where to get autocompletion suggestions)
    use('L3MON4D3/LuaSnip')         -- Snippets plugin
    use('saadparwaiz1/cmp_luasnip') -- Snippets source for nvim-cmp (where to get snippets suggestions)


    -- Gives diagnostics, pretty popups for goto definition/references/type
    use({
        "glepnir/lspsaga.nvim",
        opt = true,
        branch = "main",
        event = "LspAttach",
        config = function()
            require("lspsaga").setup({
                finder = {
                    keys = {
                        vsplit = 'v',
                        split = 's',
                        quit = { "<ESC>", "q" },
                        expand_or_jump = '<cr>',
                    }
                },
                -- For peeking only
                definition = {
                    vsplit = '<C-c>v',
                    split = '<C-c>s',
                    quit = { "<ESC>", "q" },
                    edit = '<cr>',
                },
                code_action = {
                    keys = {
                        quit = "<ESC>",
                    }
                },
                rename = {
                    quit = "<ESC>",
                    in_select = false,
                },
                symbol_in_winbar = {
                    enable = false,
                }
            })
        end,
        requires = {
            { "nvim-tree/nvim-web-devicons" },
            --Please make sure you install markdown and markdown_inline parser
            { "nvim-treesitter/nvim-treesitter" }
        }
    })

    use({
        "/jose-elias-alvarez/null-ls.nvim",
    })


    -- Editing plugins
    use {
        "windwp/nvim-autopairs",
        config = function()
            require("nvim-autopairs").setup {

            }
        end
    }
    -- Navigation
    use({
        'ggandor/leap.nvim',
        requires = { 'tpope/vim-repeat', opt = true },
        keys = { "s", "S" },
        config = function()
            local leap = require "leap"
            leap.set_default_keymaps()
            leap.opts.safe_labels = {}
            leap.init_highlight(true)
        end,
    })
    -- Initialize  this after hop so that "<leader>s" in visual mode does surround
    use({
        "kylechui/nvim-surround",
        config = function()
            require("nvim-surround").setup({
                keymaps = {
                    visual = "<leader>s",
                }
            })
        end,
    })
    -- For generating docs; sometimes it doesn't work if the lsp isn't up and running
    use {
        "danymat/neogen",
        config = function()
            require('neogen').setup {}
            local neogen = require('neogen');
            local opts = { noremap = true, silent = true }
            vim.keymap.set("n", "<leader>gd", function()
                neogen.generate()
            end, opts)
        end,
        requires = "nvim-treesitter/nvim-treesitter",
        -- tag = "*"
    }
    use {
        'numToStr/Comment.nvim',
        config = function()
            require('Comment').setup {
                mappings = {
                    basic = true,
                    extra = false,
                },
                toggler = {
                    line = '<leader>gl',
                    block = '<leader>gb',
                },
                opleader = {
                    line = '<leader>gl',
                    block = '<leader>gb',
                },
            }
        end
    }


    -- Git plugins

    -- Enables using git commands in vim
    use("tpope/vim-fugitive")
    -- For showing changes in the lefthand side
    use {
        'lewis6991/gitsigns.nvim',
        config = function()
            require('gitsigns').setup {
                current_line_blame = true,
            }
        end
    }
    -- For opening a file in github - use :OpenInGHFile
    use "almo7aya/openingh.nvim"

    -- Visual plugins

    -- Editor 'theme'
    use { 'navarasu/onedark.nvim' }
    -- Editor status line
    use { 'nvim-lualine/lualine.nvim',
        requires = { 'kyazdani42/nvim-web-devicons', opt = true }
    }
    -- Shows todo comments etc
    use {
        "folke/todo-comments.nvim",
        requires = "nvim-lua/plenary.nvim",
        config = function()
            require("todo-comments").setup {
            }
        end
    }
    -- For text coloring
    use { 'nvim-treesitter/nvim-treesitter', run = ':TSUpdate all' }



    -- Automatically set up your configuration after cloning packer.nvim
    -- Put this at the end after all plugins
    -- On update, need to run :PackerSync
    if packer_bootstrap then
        require('packer').sync()
    end
end)


require('onedark').setup {
    style = 'darker'
}
vim.cmd("highlight Comment ctermfg=gray")
require('onedark').load()

-- Initializing lualine has to come after onedark in order for proper UI to take effect
require('lualine').setup {
    options = {
        icons_enabled = true,
        theme = 'dracula',
        component_separators = { left = '', right = '' },
        section_separators = { left = '', right = '' },
        disabled_filetypes = {
            statusline = {},
            winbar = {},
        },
        ignore_focus = {},
        always_divide_middle = true,
        globalstatus = false,
        refresh = {
            statusline = 1000,
            tabline = 1000,
            winbar = 1000,
        }
    },
    sections = {
        lualine_a = { 'mode' },
        lualine_b = { 'branch', 'diagnostics' },
        lualine_c = {},
        lualine_y = { 'progress' },
        lualine_z = { 'location' }
    },
    inactive_sections = {
        lualine_a = {
        },
        lualine_b = {},
        lualine_c = {},
        lualine_x = { 'location' },
        lualine_y = {},
        lualine_z = {}
    },
    winbar = {
        lualine_a = { { 'filename', path = 1 } },
        lualine_b = {},
        lualine_c = {},
        lualine_y = {},
        lualine_z = {}
    },
    inactive_winbar = {
        lualine_a = { { 'filename', path = 1 } },
        lualine_b = {},
        lualine_c = {},
        lualine_y = {},
        lualine_z = {}
    }

}

require 'nvim-treesitter.configs'.setup {
    -- A list of parser names, or "all" (the four listed parsers should always be installed)
    ensure_installed = { "javascript", "typescript", "python", "rust", "lua", "vim", "markdown",
        "markdown_inline" },

    -- Install parsers synchronously (only applied to `ensure_installed`)
    sync_install = false,

    -- Automatically install missing parsers when entering buffer
    -- Recommendation: set to false if you don't have `tree-sitter` CLI installed locally
    auto_install = true,

    -- List of parsers to ignore installing (for "all")
    --ignore_install = { "javascript" },

    ---- If you need to change the installation directory of the parsers (see -> Advanced Setup)
    -- parser_install_dir = "/some/path/to/store/parsers", -- Remember to run vim.opt.runtimepath:append("/some/path/to/store/parsers")!

    highlight = {
        -- `false` will disable the whole extension
        enable = true,
        -- NOTE: these are the names of the parsers and not the filetype. (for example if you want to
        -- disable highlighting for the `tex` filetype, you need to include `latex` in this list as this is
        -- the name of the parser)
        -- list of language that will be disabled
        --disable = { "c", "rust" },
        -- Or use a function for more flexibility, e.g. to disable slow treesitter highlight for large files
        disable = function(lang, buf)
            local max_filesize = 100 * 1024 -- 100 KB
            local ok, stats = pcall(vim.loop.fs_stat, vim.api.nvim_buf_get_name(buf))
            if ok and stats and stats.size > max_filesize then
                return true
            end
        end,
        -- Setting this to true will run `:h syntax` and tree-sitter at the same time.
        -- Set this to `true` if you depend on 'syntax' being enabled (like for indentation).
        -- Using this option may slow down your editor, and you may see some duplicate highlights.
        -- Instead of true it can also be a list of languages
        additional_vim_regex_highlighting = false,
    },
}


vim.cmd([[
  augroup packer_user_config
    autocmd!
    autocmd BufWritePost plugins.lua source <afile> | PackerCompile
  augroup end
]])

-- Setup language servers.
local capabilities = require("cmp_nvim_lsp").default_capabilities()

local lspconfig = require('lspconfig')

local custom_attach = function(client, bufnr)
    -- Do this to prevent lsp from overriding treesitter
    client.server_capabilities.semanticTokensProvider = nil
end

-- Enable some language servers with the additional completion capabilities offered by nvim-cmp
local servers = { 'clangd', 'rust_analyzer', 'pyright', 'tsserver', 'lua_ls' }
for _, lsp in ipairs(servers) do
    lspconfig[lsp].setup {
        on_attach = custom_attach,
        capabilities = capabilities,
    }
end

vim.diagnostic.get(0, { update_in_insert = true });
vim.diagnostic.get(0, { virtual_text = false });

-- luasnip setup
local luasnip = require 'luasnip'

-- nvim-cmp setup
local cmp = require 'cmp'
cmp.setup {
    snippet = {
        expand = function(args)
            luasnip.lsp_expand(args.body)
        end,
    },
    mapping = cmp.mapping.preset.insert({
        ['<C-u>'] = cmp.mapping.scroll_docs(-4), -- Up
        ['<C-d>'] = cmp.mapping.scroll_docs(4),  -- Down
        -- C-b (back) C-f (forward) for snippet placeholder navigation.
        --['<C-Space>'] = cmp.mapping.complete(),
        ['<CR>'] = cmp.mapping.confirm {
            behavior = cmp.ConfirmBehavior.Replace,
            select = true,
        },
        ['<Tab>'] = cmp.mapping(function(fallback)
            if cmp.visible() then
                cmp.select_next_item()
            elseif luasnip.expand_or_jumpable() then
                luasnip.expand_or_jump()
            else
                fallback()
            end
        end, { 'i', 's' }),
        ['<S-Tab>'] = cmp.mapping(function(fallback)
            if cmp.visible() then
                cmp.select_prev_item()
            elseif luasnip.jumpable(-1) then
                luasnip.jump(-1)
            else
                fallback()
            end
        end, { 'i', 's' }),
    }),
    sources = {
        { name = 'nvim_lsp' },
        { name = 'luasnip' },
    },
}



local augroup = vim.api.nvim_create_augroup("LspFormatting", {})
local null_ls = require('null-ls')
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
        null_ls.builtins.formatting.stylua,
        null_ls.builtins.formatting.prettier, -- https://github.com/jose-elias-alvarez/null-ls.nvim/blob/main/doc/BUILTINS.md#prettierd
        null_ls.builtins.code_actions.eslint_d

    }
})



local keymap = vim.keymap.set

-- LSP finder - Find the symbol's definition
-- If there is no definition, it will instead be hidden
-- When you use an action in finder like "open vsplit",
-- you can use <C-t> to jump back
keymap("n", "gr", "<cmd>Lspsaga lsp_finder<CR>")

-- Code action
keymap({ "n", "v" }, "<leader>ca", "<cmd>Lspsaga code_action<CR>")

-- Rename all occurrences of the hovered word for the entire file
keymap("n", "rn", "<cmd>Lspsaga rename<CR>")

-- Rename all occurrences of the hovered word for the selected files
keymap("n", "rN", "<cmd>Lspsaga rename ++project<CR>")

-- Peek definition
-- You can edit the file containing the definition in the floating window
-- It also supports open/vsplit/etc operations, do refer to "definition_action_keys"
-- It also supports tagstack
-- Use <C-t> to jump back
keymap("n", "gp", "<cmd>Lspsaga peek_definition<CR>")

-- Go to definition
keymap("n", "gd", "<cmd>Lspsaga goto_definition<CR>")

-- Peek type definition
-- You can edit the file containing the type definition in the floating window
-- It also supports open/vsplit/etc operations, do refer to "definition_action_keys"
-- It also supports tagstack
-- Use <C-t> to jump back
keymap("n", "gt", "<cmd>Lspsaga peek_type_definition<CR>")

-- Go to type definition
-- keymap("n","gt", "<cmd>Lspsaga goto_type_definition<CR>")


-- Show line diagnostics
-- You can pass argument ++unfocus to
-- unfocus the show_line_diagnostics floating window
keymap("n", "<leader>sl", "<cmd>Lspsaga show_line_diagnostics<CR>")

-- Show buffer diagnostics
keymap("n", "<leader>sb", "<cmd>Lspsaga show_buf_diagnostics<CR>")

-- Show workspace diagnostics
keymap("n", "<leader>sw", "<cmd>Lspsaga show_workspace_diagnostics<CR>")

-- Show cursor diagnostics
keymap("n", "<leader>sc", "<cmd>Lspsaga show_cursor_diagnostics<CR>")

-- Diagnostic jump
-- You can use <C-o> to jump back to your previous location
keymap("n", "[e", "<cmd>Lspsaga diagnostic_jump_prev<CR>")
keymap("n", "]e", "<cmd>Lspsaga diagnostic_jump_next<CR>")

-- Diagnostic jump with filters such as only jumping to an error
keymap("n", "[g", function()
    require("lspsaga.diagnostic"):goto_prev({ severity = vim.diagnostic.severity.ERROR })
end)
keymap("n", "]g", function()
    require("lspsaga.diagnostic"):goto_next({ severity = vim.diagnostic.severity.ERROR })
end)
keymap("n", "[t", function()
    require("lspsaga.diagnostic"):goto_prev({ severity = { max = vim.diagnostic.severity.WARN } })
end)
keymap("n", "]t", function()
    require("lspsaga.diagnostic"):goto_next({ severity = { max = vim.diagnostic.severity.WARN } })
end)

-- Toggle outline
keymap("n", "<leader>o", "<cmd>Lspsaga outline<CR>")

-- Hover Doc
-- If there is no hover doc,
-- there will be a notification stating that
-- there is no information available.
-- To disable it just use ":Lspsaga hover_doc ++quiet"
-- Pressing the key twice will enter the hover window
keymap("n", "K", "<cmd>Lspsaga hover_doc<CR>")

-- If you want to keep the hover window in the top right hand corner,
-- you can pass the ++keep argument
-- Note that if you use hover with ++keep, pressing this key again will
-- close the hover window. If you want to jump to the hover window
-- you should use the wincmd command "<C-w>w"
-- keymap("n", "K", "<cmd>Lspsaga hover_doc ++keep<CR>")

-- Call hierarchy
keymap("n", "<Leader>ci", "<cmd>Lspsaga incoming_calls<CR>")
keymap("n", "<Leader>co", "<cmd>Lspsaga outgoing_calls<CR>")

-- Floating terminal
keymap({ "n", "t" }, "<A-d>", "<cmd>Lspsaga term_toggle<CR>")
