local M = {}

function M.setup()
    require('onedark').setup({
        style = 'darker'
    })
    vim.cmd("highlight Comment ctermfg=gray")
    require('onedark').load()
end


return M
