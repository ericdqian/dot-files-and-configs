local M = {}

local parser_names = {
    "javascript",
    "typescript",
    "python",
    "rust",
    "lua",
    "vim",
    "markdown",
    "markdown_inline",
}

local max_filesize = 500 * 1024
local setup_current_treesitter
local setup_legacy_treesitter
local is_large_file

function M.setup()
    local treesitter = require("nvim-treesitter")
    if type(treesitter.install) == "function" then
        setup_current_treesitter(treesitter)
    else
        setup_legacy_treesitter()
    end

    vim.api.nvim_create_user_command("Ti", function(opts)
        vim.cmd("TSInstall " .. opts.args)
    end, { nargs = "+" })
    vim.api.nvim_create_user_command("Tu", function(opts)
        vim.cmd("TSUninstall " .. opts.args)
    end, { nargs = "+" })
end

function setup_current_treesitter(treesitter)
    treesitter.setup({
        install_dir = vim.fn.stdpath("data") .. "/site",
    })
    treesitter.install(parser_names)

    vim.api.nvim_create_autocmd("FileType", {
        group = vim.api.nvim_create_augroup("UserTreesitter", { clear = true }),
        callback = function(args)
            if is_large_file(args.buf) then
                return
            end

            pcall(vim.treesitter.start, args.buf)
        end,
    })
end

function setup_legacy_treesitter()
    require("nvim-treesitter.configs").setup({
        ensure_installed = parser_names,
        sync_install = false,
        auto_install = true,
        highlight = {
            enable = true,
            disable = function(_, buf)
                return is_large_file(buf)
            end,
            additional_vim_regex_highlighting = false,
        },
    })
end

function is_large_file(buf)
    local uv = vim.uv or vim.loop
    local ok, stats = pcall(uv.fs_stat, vim.api.nvim_buf_get_name(buf))
    return ok and stats and stats.size > max_filesize
end

return M
