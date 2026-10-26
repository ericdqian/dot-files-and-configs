local M = {}

function M.setup()
    local capabilities = require("cmp_nvim_lsp").default_capabilities()

    local custom_attach = function(client, bufnr)
        -- Do this to prevent lsp from overriding treesitter
        client.server_capabilities.semanticTokensProvider = nil
    end

    vim.lsp.config("*", {
        on_attach = custom_attach,
        capabilities = capabilities,
    })

    local servers = {
        "marksman",
        "clangd",
        "rust_analyzer",
        "tflint",
        "bashls",
        "terraformls",
    }

    vim.lsp.config("lua_ls", {
        settings = {
            Lua = {
                runtime = { version = "LuaJIT" },
                diagnostics = { globals = { "vim" } },
                workspace = {
                    -- Index Lua APIs, rather than every plugin's entire runtime tree.
                    library = vim.api.nvim_get_runtime_file("lua", true),
                    checkThirdParty = false,
                },
                telemetry = { enable = false },
            },
        },
    })

    local eslint_attach = function(client, bufnr)
        client.server_capabilities.semanticTokensProvider = nil
        client.server_capabilities.document_formatting = true
        -- clear = false: clearing the whole group on each attach would drop
        -- the autocmds registered for other eslint buffers.
        local au_lsp = vim.api.nvim_create_augroup("eslint_lsp", { clear = false })
        vim.api.nvim_clear_autocmds({ group = au_lsp, buffer = bufnr })
        vim.api.nvim_create_autocmd("BufWritePre", {
            buffer = bufnr,
            callback = function()
                vim.cmd("EslintFixAll")
            end,
            group = au_lsp,
        })
    end

    vim.lsp.config("eslint", {
        on_attach = eslint_attach,
    })

    vim.lsp.config("basedpyright", {
        -- A uv workspace's configuration lives above its individual packages.
        root_markers = {
            "pyrightconfig.json",
            "uv.lock",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "requirements.txt",
            "Pipfile",
            ".git",
        },
        before_init = require("config.lsp.python").configure_interpreter,
    })

    -- terraform-ls roots at the enclosing .git and indexes every directory under
    -- it, which includes each worktree's node_modules in repos like core.
    vim.lsp.config("terraformls", {
        init_options = {
            indexing = {
                ignoreDirectoryNames = { "node_modules", ".worktrees" },
            },
        },
    })

    vim.lsp.config("ts_ls", {
        on_attach = function(client, bufnr)
            custom_attach(client, bufnr)
            -- Prettier via null-ls owns TypeScript formatting.
            client.server_capabilities.documentFormattingProvider = false
            client.server_capabilities.documentRangeFormattingProvider = false
        end,
        init_options = {
            preferences = {
                importModuleSpecifierPreference = "non-relative",
            },
        },
    })

    vim.lsp.enable(vim.list_extend({ "lua_ls", "eslint", "basedpyright", "ts_ls" }, servers))

    vim.diagnostic.config({
        update_in_insert = true,
        virtual_text = false,
    })
end

return M
