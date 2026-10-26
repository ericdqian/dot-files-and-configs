-- Run from the repository root: nvim --headless -u NONE -l nvim_config/tests/python_lsp.lua
vim.opt.runtimepath:prepend(vim.fn.getcwd() .. "/nvim_config")
package.preload.cmp_nvim_lsp = function()
    return {
        default_capabilities = function()
            return {}
        end,
    }
end

require("config.lsp.init").setup()
local python_lsp = require("config.lsp.python")
local fixture_root = vim.fn.tempname()

local function write_fixture(relative_path, content)
    local fixture_path = vim.fs.joinpath(fixture_root, relative_path)
    vim.fn.mkdir(vim.fs.dirname(fixture_path), "p")
    vim.fn.writefile({ content }, fixture_path)
    return fixture_path
end

local succeeded, failure = pcall(function()
    local first_source = write_fixture("first/python/packages/worker/src/worker.py", "")
    write_fixture("first/python/packages/worker/pyproject.toml", "[project]")
    write_fixture("first/python/pyproject.toml", "[tool.basedpyright]")
    write_fixture("first/python/uv.lock", "")
    write_fixture("first/.nvimrc", '{"python":{"interpreter_path":"python/.venv/bin/python"}}')

    local second_source = write_fixture("second/python/packages/worker/src/worker.py", "")
    write_fixture("second/python/packages/worker/pyproject.toml", "[project]")
    write_fixture("second/python/uv.lock", "")
    write_fixture("second/.nvimrc", '{"python":{"interpreter_path":"/custom/second/python"}}')

    -- Startup and the current buffer must not determine later clients' interpreters.
    vim.cmd.edit(first_source)
    local first_root = vim.fs.root(first_source, vim.lsp.config.basedpyright.root_markers)
    local second_root = vim.fs.root(second_source, vim.lsp.config.basedpyright.root_markers)
    assert(
        first_root == vim.fs.joinpath(fixture_root, "first/python"),
        "nested package hid workspace config"
    )
    assert(
        second_root == vim.fs.joinpath(fixture_root, "second/python"),
        "second workspace root was wrong"
    )

    local shared_settings = { python = { analysis = { autoSearchPaths = true } } }
    local first_client_config = { root_dir = first_root, settings = vim.deepcopy(shared_settings) }
    local first_client_settings = first_client_config.settings
    python_lsp.configure_interpreter({}, first_client_config)
    assert(
        first_client_settings == first_client_config.settings,
        "LSP client lost its settings reference"
    )
    assert(
        first_client_settings.python.pythonPath
            == vim.fs.joinpath(fixture_root, "first/python/.venv/bin/python")
    )
    assert(
        first_client_settings.python.analysis.autoSearchPaths,
        "existing Python settings were lost"
    )

    local second_client_config =
        { root_dir = second_root, settings = vim.deepcopy(shared_settings) }
    python_lsp.configure_interpreter({}, second_client_config)
    assert(
        second_client_config.settings.python.pythonPath == "/custom/second/python",
        "used current buffer's interpreter"
    )
    assert(shared_settings.python.pythonPath == nil, "shared server settings were modified")

    local standalone_source = write_fixture("standalone/src/worker.py", "")
    write_fixture("standalone/pyproject.toml", "[project]")
    local standalone_root = vim.fs.root(standalone_source, vim.lsp.config.basedpyright.root_markers)
    assert(
        standalone_root == vim.fs.joinpath(fixture_root, "standalone"),
        "non-uv project root regressed"
    )
    write_fixture("standalone/.nvimrc", "invalid json")
    local standalone_python = write_fixture("standalone/.venv/bin/python", "#!/bin/sh")
    vim.fn.setfperm(standalone_python, "rwx------")
    local standalone_client = { root_dir = standalone_root, settings = {} }
    python_lsp.configure_interpreter({}, standalone_client)
    assert(
        standalone_client.settings.python.pythonPath == standalone_python,
        "local venv fallback failed"
    )

    local rootless_client = { settings = {} }
    python_lsp.configure_interpreter({}, rootless_client)
    assert(
        rootless_client.settings.python.pythonPath == vim.fn.exepath("python3"),
        "PATH fallback failed"
    )
end)

vim.fn.delete(fixture_root, "rf")
assert(succeeded, failure)
print("Python LSP workspace checks passed")
