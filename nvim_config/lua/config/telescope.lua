local M = {}

function M.setup()
    local builtin = require("telescope.builtin")
    vim.keymap.set("n", "<leader>z", builtin.find_files, {})
    vim.keymap.set("n", "<leader>a", builtin.live_grep, {})
    vim.keymap.set("n", ";", builtin.buffers, {})
    vim.keymap.set("n", "<leader>q", builtin.resume, {})
    local telescope = require("telescope")
    local actions = require("telescope.actions")
    local transform_mod = require("telescope.actions.mt").transform_mod

    telescope.setup({
        defaults = {
            mappings = {
                i = {
                    ["<C-s>"] = actions.select_horizontal, -- Split horizontally with selection
                    ["<A-BS>"] = function() -- Overwrite alt+backspace in insert mode to do bulk delete
                        vim.cmd([[normal! bcw]])
                    end,
                    -- ["<esc>"] = function(prompt_bufnr)
                    --     local telescope_state = require('telescope.actions.state');
                    --     print("prompt", prompt_bufnr)
                    --     print("telescope state", telescope_state)
                    --     local current_picker = telescope_state.get_current_picker(prompt_bufnr)
                    --     local prompt = current_picker:_get_prompt()
                    --     if prompt == "a" then actions.close() end
                    -- end
                },
            },
        },
        pickers = {
            buffers = {
                sort_mru = true,
                -- sort_lastused = true, -- This is referring to where the selector is placed
                ignore_current_buffer = false,
            },
            find_files = {
                sort_mru = true,
            },
        },
    })
end

return M
