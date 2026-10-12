local M = {}

local install_lsp_position_compat
local install_saga_request_compat

function M.setup()
    install_lsp_position_compat()

    require("lspsaga").setup({
        finder = {
            keys = {
                vsplit = "v",
                split = "s",
                quit = { "<ESC>", "q" },
                toggle_or_open = "<cr>",
            },
        },
        -- For peeking only
        definition = {
            vsplit = "<C-c>v",
            split = "<C-c>s",
            quit = { "<ESC>", "q" },
            edit = "<cr>",
        },
        code_action = {
            keys = {
                quit = "<ESC>",
            },
        },
        rename = {
            quit = "<ESC>",
            in_select = false,
        },
        lightbulb = {
            enable = false, -- TODO: reenable when we find a way to prevent it from shifting the horizontal buffer in a file with no changes.
        },
    })

    install_saga_request_compat()

    local keymap = vim.keymap.set

    -- LSP finder - Find the symbol's definition
    -- If there is no definition, it will instead be hidden
    -- When you use an action in finder like "open vsplit",
    -- you can use <C-t> to jump back
    keymap("n", "gr", "<cmd>Lspsaga finder<CR>")

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
        require("lspsaga.diagnostic"):goto_prev({
            severity = { max = vim.diagnostic.severity.WARN },
        })
    end)
    keymap("n", "]t", function()
        require("lspsaga.diagnostic"):goto_next({
            severity = { max = vim.diagnostic.severity.WARN },
        })
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
end

function install_lsp_position_compat()
    if vim.lsp.util._get_line_byte_from_position ~= nil then
        return
    end
    if vim.pos == nil or vim.pos.lsp == nil then
        return
    end

    -- lspsaga still calls this removed private helper on current Neovim nightlies.
    vim.lsp.util._get_line_byte_from_position = function(bufnr, position, offset_encoding)
        return vim.pos.lsp(bufnr, position, offset_encoding or "utf-16").col
    end
end

function install_saga_request_compat()
    local definition = require("lspsaga.definition")
    local definition_request = definition.definition_request
    -- Patch Saga's singleton methods: upstream sets pending even with no request recipients.
    definition.definition_request = function(saga_definition, method, handler, args)
        if #vim.lsp.get_clients({ bufnr = 0, method = method }) == 0 then
            vim.notify(
                "[lspsaga] " .. method .. " is not supported in this buffer",
                vim.log.levels.WARN
            )
            return
        end
        return definition_request(saga_definition, method, handler, args)
    end

    local code_action = require("lspsaga.codeaction")
    local send_request = code_action.send_request
    -- Supply diagnostics through the public API before Saga reaches its removed API fallback.
    code_action.send_request = function(saga_action, buffer, options, callback)
        local request_options = vim.deepcopy(options or {})
        if request_options.diagnostics or request_options.only then
            request_options = { options = request_options }
        end
        request_options.context = request_options.context or {}
        if request_options.context.diagnostics == nil then
            request_options.context.diagnostics =
                vim.lsp.diagnostic.from(vim.diagnostic.get(buffer, {
                    lnum = vim.api.nvim_win_get_cursor(0)[1] - 1,
                }))
        end
        return send_request(saga_action, buffer, request_options, callback)
    end

    local request_code_action = code_action.code_action
    -- Saga owns this state; clear its lock on synchronous failure so the next action can run.
    code_action.code_action = function(saga_action, options)
        if #vim.lsp.get_clients({ bufnr = 0, method = "textDocument/codeAction" }) == 0 then
            vim.notify(
                "[lspsaga] code actions are not supported in this buffer",
                vim.log.levels.WARN
            )
            return
        end
        local ok, request_error = pcall(request_code_action, saga_action, vim.deepcopy(options))
        if not ok then
            saga_action.pending_request = false
            error(request_error, 0)
        end
    end
end

return M
