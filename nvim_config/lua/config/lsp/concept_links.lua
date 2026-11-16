local M = {}
local read_json
local nearest_file
local cited_commit

-- Resolution intentionally loads historical buffers so LSP consumers can open them.
function M.resolve_and_load_location(link_target, source_path)
    local repository_key, repository_path, fragment =
        link_target:match("^concept://([^/]+/[^/]+)/([^#]+)#?(.*)$")
    assert(repository_key, "Malformed concept link: " .. link_target)
    repository_path = repository_path:gsub("%%(%x%x)", function(hex_byte)
        return string.char(tonumber(hex_byte, 16))
    end)
    assert(
        not repository_path:match("^/")
            and not repository_path:find("%z")
            and not ("/" .. repository_path .. "/"):find("/%.%./"),
        "Invalid concept path"
    )
    local line_number = fragment == "" and 1 or tonumber(fragment:match("^L(%d+)$"))
    assert(line_number and line_number > 0, "Unsupported concept anchor: " .. fragment)
    local registry = read_json(vim.fn.expand("~/learning/repositories.json"))
    local overrides = read_json(nearest_file(source_path, ".concept-links.json"))
    local registry_location = (registry.repositories or {})[repository_key]
    local override_location = (overrides.repositories or {})[repository_key]
    local checkout_location = override_location and vim.fn.expand(override_location)
    if not checkout_location or vim.fn.isdirectory(checkout_location) ~= 1 then
        checkout_location = registry_location and vim.fn.expand(registry_location)
    end
    assert(checkout_location, "Unknown repository key: " .. repository_key)
    local target_path = vim.fs.joinpath(checkout_location, repository_path)
    local target_uri = vim.uri_from_fname(target_path)
    if vim.fn.filereadable(target_path) ~= 1 then
        local commit = cited_commit(source_path, repository_key)
        assert(commit, "No cited commit for " .. repository_key .. "/" .. repository_path)
        assert(
            registry_location,
            "No registry location for historical repository: " .. repository_key
        )
        local git_result = vim.system({
            "git",
            "-C",
            vim.fn.expand(registry_location),
            "show",
            commit .. ":" .. repository_path,
        }, { text = true }):wait()
        assert(
            git_result.code == 0,
            "Cited commit or file unavailable: "
                .. commit
                .. ":"
                .. repository_path
                .. " ("
                .. (git_result.stderr or "")
                .. ")"
        )
        target_uri = "concept-revision://"
            .. repository_key
            .. "/"
            .. commit
            .. "/"
            .. repository_path
        local target_bufnr = vim.uri_to_bufnr(target_uri)
        vim.fn.bufload(target_bufnr)
        vim.bo[target_bufnr].readonly = false
        vim.bo[target_bufnr].modifiable = true
        local historical_lines = vim.split(git_result.stdout, "\n", { plain = true })
        if historical_lines[#historical_lines] == "" then
            table.remove(historical_lines)
        end
        vim.api.nvim_buf_set_lines(target_bufnr, 0, -1, false, historical_lines)
        vim.bo[target_bufnr].buftype = "nofile"
        vim.bo[target_bufnr].swapfile = false
        vim.bo[target_bufnr].modified = false
        vim.bo[target_bufnr].readonly = true
        vim.bo[target_bufnr].modifiable = false
        vim.bo[target_bufnr].filetype = vim.filetype.match({ filename = repository_path }) or ""
    end
    local position = { line = line_number - 1, character = 0 }
    return { uri = target_uri, range = { start = position, ["end"] = position } }
end

function read_json(json_path)
    if not json_path or vim.fn.filereadable(json_path) ~= 1 then
        return {}
    end
    local decoded = vim.json.decode(table.concat(vim.fn.readfile(json_path), "\n"))
    assert(type(decoded) == "table", "Invalid JSON object: " .. json_path)
    return decoded
end

function nearest_file(source_path, filename)
    return vim.fs.find(
        filename,
        { path = vim.fs.dirname(source_path), upward = true, type = "file" }
    )[1]
end

function cited_commit(source_path, repository_key)
    local revision = read_json(nearest_file(source_path, "revision.json"))
    if type(revision.pr) == "string" and revision.pr:match("^([^/]+/[^/]+)/") == repository_key then
        if type(revision.head) == "string" and revision.head:match("^%x+$") then
            return revision.head
        end
    end
    -- A run's commit belongs only to its PR repository.
    if revision.pr ~= nil then
        return nil
    end
    local document_lines = vim.fn.readfile(source_path)
    if document_lines[1] ~= "---" then
        return nil
    end
    for line_index = 2, #document_lines do
        if document_lines[line_index] == "---" then
            break
        end
        local verified_commit =
            document_lines[line_index]:match("^verified_at:%s*[\"']?(%x+)[\"']?%s*$")
        if verified_commit then
            return verified_commit
        end
    end
end

return M
