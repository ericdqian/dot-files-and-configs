vim.api.nvim_set_keymap(
    "n",
    "gr",
    ":lua require('vscode-neovim').action('editor.action.goToReferences')<CR>",
    { noremap = true, silent = true }
)

vim.api.nvim_set_keymap(
    "n",
    "gt",
    ":lua require('vscode-neovim').action('editor.action.goToTypeDefinition')<CR>",
    { noremap = true, silent = true }
)

vim.api.nvim_set_keymap(
    "n",
    "<leader>rn",
    ":lua require('vscode-neovim').action('editor.action.rename')<CR>",
    { noremap = true, silent = true }
)

vim.api.nvim_set_keymap(
    "n",
    "-",
    ":lua require('vscode-neovim').action('workbench.view.explorer')<CR>",
    { noremap = true, silent = true }
)

vim.api.nvim_set_keymap(
    "n",
    "-",
    ":lua require('vscode-neovim').action('workbench.view.explorer')<CR>",
    { noremap = true, silent = true }
)

vim.api.nvim_set_keymap(
    "n",
    "<leader>a",
    ":lua require('vscode-neovim').action('workbench.action.findInFiles')<CR>",
    { noremap = true, silent = true }
)

-- -- Use the native plugin
-- vim.api.nvim_set_keymap(
--     "n",
--     "s",
--     ":lua require('vscode-neovim').action('leap.findForward')<CR>",
--     { noremap = true, silent = true }
-- )
--
-- vim.api.nvim_set_keymap(
--     "n",
--     "S",
--     ":lua require('vscode-neovim').action('leap.findBackward')<CR>",
--     { noremap = true, silent = true }
-- )

vim.api.nvim_set_keymap(
    "n",
    "]g",
    ":lua require('vscode-neovim').action('editor.action.marker.next')<CR>",
    { noremap = true, silent = true }
)

vim.api.nvim_set_keymap(
    "n",
    "[g",
    ":lua require('vscode-neovim').action('editor.action.marker.prev')<CR>",
    { noremap = true, silent = true }
)

vim.api.nvim_set_keymap(
    "n",
    "<leader>q",
    ":lua require('vscode-neovim').action('workbench.action.closeEditorsInGroup')<CR>",
    { noremap = true, silent = true }
)

local comment_shortcuts = { "<leader>gb", "<leader>gl" }

function visual_comment_selected_lines()
    local vscode = require("vscode-neovim")
    local start_line = vim.fn.line("'<")
    local end_line = vim.fn.line("'>")

    if end_line < start_line then
        start_line = end_line
        end_line = start_line - 1
    end

    local range = { start_line - 1, end_line - 1 }

    vscode.action("editor.action.commentLine", { range = range })
end

for _, shortcut in ipairs(comment_shortcuts) do
    vim.api.nvim_set_keymap("v", shortcut, ":lua visual_comment_selected_lines()<CR>", {})
end

function normal_comment_selected_lines()
    local vscode = require("vscode-neovim")
    local curr_line = vim.fn.line(".") - 1

    local range = { curr_line, curr_line }

    vscode.action("editor.action.commentLine", { range = range })
end

for _, shortcut in ipairs(comment_shortcuts) do
    vim.api.nvim_set_keymap("n", shortcut, ":lua normal_comment_selected_lines()<CR>", {})
end
