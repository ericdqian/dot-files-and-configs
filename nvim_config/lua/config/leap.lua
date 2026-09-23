local M = {}

function M.setup()
    local leap = require("leap")
    vim.keymap.set({ "n", "x", "o" }, "s", "<Plug>(leap-forward)")
    vim.keymap.set({ "n", "x", "o" }, "S", "<Plug>(leap-backward)")
    vim.keymap.set({ "x", "o" }, "x", "<Plug>(leap-forward-next-to)")
    vim.keymap.set({ "x", "o" }, "X", "<Plug>(leap-backward-next-to)")
    vim.keymap.set({ "n", "x", "o" }, "gs", "<Plug>(leap-from-window)")
    leap.init_hl()
end

return M
