local M = {}

local get_python_path

function M.configure_interpreter(_, client_config)
    -- Neovim's before_init API requires updating this client's private config.
    -- Resolve from its root, since the current buffer may belong to another project.
    client_config.settings = client_config.settings or {}
    client_config.settings.python =
        vim.tbl_deep_extend("force", client_config.settings.python or {}, {
            pythonPath = get_python_path(client_config.root_dir),
        })
end

function get_python_path(project_root)
    if project_root then
        local config_path =
            vim.fs.find(".nvimrc", { path = project_root, upward = true, type = "file" })[1]
        if config_path then
            local config_file = io.open(config_path, "r")
            if config_file then
                local config_content = config_file:read("*a")
                config_file:close()
                local decoded, project_config = pcall(vim.json.decode, config_content)
                local python_config = decoded
                    and type(project_config) == "table"
                    and project_config.python
                local interpreter_path = type(python_config) == "table"
                    and python_config.interpreter_path
                if type(interpreter_path) == "string" and interpreter_path ~= "" then
                    if vim.startswith(interpreter_path, "/") then
                        return interpreter_path
                    end
                    return vim.fs.normalize(
                        vim.fs.joinpath(vim.fs.dirname(config_path), interpreter_path)
                    )
                end
            end
        end

        local project_python = vim.fs.joinpath(project_root, ".venv", "bin", "python")
        if vim.fn.executable(project_python) == 1 then
            return project_python
        end
    end

    return vim.fn.exepath("python3")
end

return M
