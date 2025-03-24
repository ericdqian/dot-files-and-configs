local M = {}

function M.setup()
    require("lualine").setup({
        options = {
            icons_enabled = true,
            theme = "dracula",
            component_separators = { left = "", right = "" },
            section_separators = { left = "", right = "" },
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
            },
        },
        sections = {
            lualine_a = { "mode" },
            lualine_b = { "branch", "diagnostics" },
            lualine_c = {},
            lualine_y = { "progress" },
            lualine_z = { "location" },
        },
        inactive_sections = {
            lualine_a = {},
            lualine_b = {},
            lualine_c = {},
            lualine_x = { "location" },
            lualine_y = {},
            lualine_z = {},
        },
        winbar = {
            lualine_a = { { "filename", path = 1 } },
            lualine_b = {},
            lualine_c = {},
            lualine_y = {},
            lualine_z = {},
        },
        inactive_winbar = {
            lualine_a = { { "filename", path = 1 } },
            lualine_b = {},
            lualine_c = {},
            lualine_y = {},
            lualine_z = {},
        },
    })
end

return M
