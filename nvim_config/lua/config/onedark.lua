local M = {}

function M.setup()
    require("onedark").setup({
        style = "darker",
        transparent = true,
    })
    vim.cmd("highlight Comment ctermfg=gray")
    require("onedark").load()
    M.clear_backgrounds({ "NormalFloat", "FloatBorder" })
end

-- Retain themed foregrounds while allowing the terminal background to show in floats.
function M.clear_backgrounds(groups)
    for _, group in ipairs(groups) do
        local highlight = vim.api.nvim_get_hl(0, { name = group, link = false })
        vim.api.nvim_set_hl(0, group, vim.tbl_extend("force", {}, highlight, { bg = "NONE" }))
    end
end

return M
