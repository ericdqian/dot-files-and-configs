local M = {}

function M.setup()
    require("onedark").setup({
        style = "darker",
        highlights = {
            RenderMarkdownConceptLink = { fg = "$blue" },
            RenderMarkdownCodeLink = { fg = "$yellow" },
        },
    })
    vim.cmd("highlight Comment ctermfg=gray")
    require("onedark").load()
end

return M
