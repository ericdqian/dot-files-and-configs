local M = {}

local DEFAULT_PYTHON = vim.fn.exepath("python3") -- Forces pyright to use the same python as the activated venv instead of potentially `python3`

local config_file_name = ".nvimrc"

local function get_python_path()
    local null_ls_utils = require("null-ls.utils") -- TODO: figure out how to not use null-ls.utils since it's technically not a lsp thing. Maybe copy it? Should also consolidate this utility function to retrieving arbitrary object paths from the json object.
    local root_path = null_ls_utils.root_pattern(config_file_name)(vim.api.nvim_buf_get_name(0))
    if root_path == nil then
        return DEFAULT_PYTHON
    end
    local config_path = root_path .. "/" .. config_file_name
    local config_file = io.open(config_path, "r")
    if config_file == nil then
        return DEFAULT_PYTHON
    end
    local raw_config_content = config_file:read("*a")
    local config_content = vim.fn.json_decode(raw_config_content)
    if config_content == nil then
        return DEFAULT_PYTHON
    end
    if config_content["python"] == nil then
        print(
            "Warning: no Python section in project's .nvimrc config. Check .nvimrc in the project root"
        )
        return DEFAULT_PYTHON
    end
    if config_content["python"]["interpreter_path"] == nil then
        print(
            "Warning: no interpreter_path in project's .nvimrc config. Check .nvimrc in the project root"
        )
        return DEFAULT_PYTHON
    end
    local full_interpreter_path = root_path .. "/" .. config_content["python"]["interpreter_path"]

    return full_interpreter_path
end

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
                    library = vim.api.nvim_get_runtime_file("", true),
                },
                telemetry = { enable = false },
            },
        },
    })

    local eslint_attach = function(client, bufnr)
        client.server_capabilities.semanticTokensProvider = nil
        client.server_capabilities.document_formatting = true
        if client.server_capabilities.document_formatting then
            local au_lsp = vim.api.nvim_create_augroup("eslint_lsp", { clear = true })
            vim.api.nvim_create_autocmd("BufWritePre", {
                pattern = "*",
                callback = function()
                    vim.cmd("EslintFixAll")
                end,
                group = au_lsp,
            })
        end
    end

    vim.lsp.config("eslint", {
        on_attach = eslint_attach,
    })

    vim.lsp.config("pyright", {
        settings = {
            python = {
                pythonPath = get_python_path(),
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

    vim.lsp.enable(vim.list_extend({ "lua_ls", "eslint", "pyright", "ts_ls" }, servers))

    vim.diagnostic.config({
        update_in_insert = true,
        virtual_text = false,
    })
end

return M
