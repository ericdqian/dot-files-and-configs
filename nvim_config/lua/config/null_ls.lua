--[[

There is a custom .null_ls.nvim file in the project root that specifies the paths to the config files so that we can infer which formatters and diagonstic packages to use.

The format should look like this:

{
    "python": {
        "pyproject_toml_path": "python/pyproject.toml"
    },
    "typescript": {
        "prettier_path": "typescript/.prettierrc.json"
    }
}

]]

local M = {}

local config_file_name = ".nvimrc"

local function read_nvimrc_config()
    local null_ls_utils = require("null-ls.utils")
    local root_path = null_ls_utils.root_pattern(config_file_name)(vim.api.nvim_buf_get_name(0))
    if root_path == nil then
        return nil, "Root path not found"
    end
    local config_path = root_path .. "/" .. config_file_name
    local config_file = io.open(config_path, "r")
    if config_file == nil then
        return nil, "Config file not found"
    end
    local raw_config_content = config_file:read("*a")
    local config_content = vim.fn.json_decode(raw_config_content)
    if config_content == nil then
        return nil, "Failed to decode JSON"
    end
    return config_content, nil
end

local function should_mount_python_source(source_name)
    local config_content, err = read_nvimrc_config()
    if config_content == nil then
        return false
    end
    if config_content["python"] == nil then
        print(
            "Warning: no Python section in project's .nvimrc config. Check .nvimrc in the project root"
        )
        return false
    end
    if config_content["python"]["pyproject_toml_path"] == nil then
        print(
            "Warning: no pyproject_toml_path in project's .nvimrc config. Check .nvimrc in the project root"
        )
        return false
    end
    local python_config_file_path = root_path
        .. "/"
        .. config_content["python"]["pyproject_toml_path"]

    local python_config_file = io.open(python_config_file_path, "r")
    if python_config_file == nil then
        return false
    end
    local python_config_file_raw_content = python_config_file:read("*a")

    local pattern = "tool." .. source_name
    return python_config_file_raw_content:find(pattern) ~= nil
end

local function should_mount_typescript_source(source_name)
    local config_content, err = read_nvimrc_config()
    if config_content == nil then
        print("Error: " .. err)
        return false
    end
    if config_content["typescript"] == nil then
        print(
            "Warning: no TypeScript section in project's .nvimrc config. Check .nvimrc in the project root"
        )
        return false
    end
    if config_content["typescript"]["prettier_path"] == nil then
        print(
            "Warning: no prettier_path in project's .nvimrc config. Check .nvimrc in the project root"
        )
        return false
    end
    local typescript_config_file_path = root_path
        .. "/"
        .. config_content["typescript"]["prettier_path"]

    local typescript_config_file = io.open(typescript_config_file_path, "r")
    if typescript_config_file == nil then
        return false
    end
    local typescript_config_file_raw_content = typescript_config_file:read("*a")

    local pattern = "tool." .. source_name
    return typescript_config_file_raw_content:find(pattern) ~= nil
end

function M.setup()
    local augroup = vim.api.nvim_create_augroup("LspFormatting", {})
    local null_ls = require("null-ls")
    null_ls.setup({
        -- you can reuse a shared lspconfig on_attach callback here
        on_attach = function(client, bufnr)
            if client.supports_method("textDocument/formatting") then
                vim.api.nvim_clear_autocmds({ group = augroup, buffer = bufnr })
                vim.api.nvim_create_autocmd("BufWritePre", {
                    group = augroup,
                    buffer = bufnr,
                    callback = function()
                        vim.lsp.buf.format({ bufnr = bufnr })
                        -- vim.lsp.buf.formatting_sync()
                    end,
                })
            end
        end,
        sources = {
            null_ls.builtins.formatting.stylua, --  brew install stylua
            require("none-ls.formatting.rustfmt"), --  rustup component add rustfmt
            null_ls.builtins.formatting.prettier.with({
                filetypes = { "javascript", "typescript", "json" },
            }),
            -- require("none-ls.diagnostics.eslint"), --  installed on a per project basis
            require("none-ls.diagnostics.flake8").with({
                filetypes = { "python" },
                condition = function()
                    return should_mount_python_source("flake8")
                end,
            }),
            require("none-ls.diagnostics.ruff").with({
                filetypes = { "python" },
                condition = function()
                    return should_mount_python_source("ruff")
                end,
            }),
            null_ls.builtins.formatting.black.with({
                filetypes = { "python" },
                condition = function()
                    return should_mount_python_source("black")
                end,
            }),
            null_ls.builtins.formatting.terraform_fmt,
        },
    })
end

return M
