-- Run: nvim --headless -u NONE -i NONE -l nvim_config/tests/concept_links.lua
vim.opt.runtimepath:prepend(vim.fn.getcwd() .. "/nvim_config")
vim.opt.runtimepath:append(vim.fn.stdpath("data") .. "/site")
vim.opt.runtimepath:append(vim.fn.stdpath("data") .. "/lazy/nvim-treesitter")
local fixture_root = vim.fn.resolve(vim.fn.tempname())
local original_home = vim.env.HOME
local original_notify = vim.notify
local resolve_and_load_location = require("config.lsp.concept_links").resolve_and_load_location

local function write_fixture(relative_path, lines)
    local fixture_path = fixture_root .. "/" .. relative_path
    vim.fn.mkdir(vim.fs.dirname(fixture_path), "p")
    vim.fn.writefile(lines, fixture_path)
    return fixture_path
end

local function write_json(relative_path, value)
    return write_fixture(relative_path, { vim.json.encode(value) })
end

local function git(arguments)
    local command = { "git", "-C", fixture_root .. "/default" }
    vim.list_extend(command, arguments)
    local result = vim.system(command, { text = true }):wait()
    assert(result.code == 0, result.stderr)
    return vim.trim(result.stdout)
end

local succeeded, failure = xpcall(function()
    vim.env.HOME = fixture_root
    local default_path = write_fixture("default/source file.lua", { "-- default", "return 42" })
    local override_path = write_fixture("override/source file.lua", { "-- override", "return 99" })
    local source_path = write_fixture("run/docs/explanation.md", {
        "[source](concept://owner/repo/source%20file.lua#L2)",
        "[unknown](concept://unknown/repo/file.lua)",
    })
    write_json(
        "learning/repositories.json",
        { repositories = { ["owner/repo"] = fixture_root .. "/default" } }
    )
    write_json(
        "run/.concept-links.json",
        { repositories = { ["owner/repo"] = fixture_root .. "/override" } }
    )
    local link = "concept://owner/repo/source%20file.lua#L2"
    local function assert_open_path(expected_path)
        vim.cmd.edit(source_path)
        local location = resolve_and_load_location(link, source_path)
        assert(vim.uri_to_fname(location.uri) == expected_path, vim.inspect(location))
        assert(vim.lsp.util.show_document(location, "utf-16", { focus = true }))
        assert(vim.api.nvim_buf_get_name(0) == expected_path)
        assert(vim.api.nvim_win_get_cursor(0)[1] == 2)
    end
    assert_open_path(override_path)
    -- The nearest override is authoritative even when it does not contain this key.
    write_json("run/docs/.concept-links.json", { repositories = {} })
    assert_open_path(default_path)
    vim.fn.delete(fixture_root .. "/run/docs/.concept-links.json")
    vim.fn.delete(fixture_root .. "/override", "rf")
    assert_open_path(default_path)
    vim.fn.delete(fixture_root .. "/run/.concept-links.json")
    assert_open_path(default_path)
    git({ "init", "-q" })
    git({ "add", "source file.lua" })
    git({
        "-c",
        "user.name=Resolver Test",
        "-c",
        "user.email=resolver@example.invalid",
        "commit",
        "-qm",
        "fixture",
    })
    local commit = git({ "rev-parse", "HEAD" })
    write_json("run/revision.json", { pr = "owner/repo/123", head = commit })
    vim.fn.delete(default_path)
    -- An existing override without this file must read history from the registry repository.
    vim.fn.mkdir(fixture_root .. "/override", "p")
    write_json(
        "run/.concept-links.json",
        { repositories = { ["owner/repo"] = fixture_root .. "/override" } }
    )
    local historical_location = resolve_and_load_location(link, source_path)
    assert(vim.lsp.util.show_document(historical_location, "utf-16", { focus = true }))
    assert(vim.api.nvim_get_current_line() == "return 42")
    assert(vim.bo.readonly and not vim.bo.modifiable and vim.bo.buftype == "nofile")
    assert(vim.bo.filetype == "lua" and not vim.bo.swapfile and not vim.bo.modified)
    assert(resolve_and_load_location(link, source_path).uri == historical_location.uri)
    vim.fn.delete(fixture_root .. "/run/revision.json")
    local concept_path =
        write_fixture("concept.md", { "---", 'verified_at: "' .. commit .. '"', "---", "Concept" })
    assert(resolve_and_load_location(link, concept_path).uri == historical_location.uri)

    local function assert_failure(target, document, message)
        local resolved, resolution_error = pcall(resolve_and_load_location, target, document)
        assert(
            not resolved and tostring(resolution_error):find(message, 1, true),
            tostring(resolution_error)
        )
    end
    assert_failure("concept://unknown/repo/file.lua", source_path, "Unknown repository key")
    assert_failure(link, source_path, "No cited commit")
    write_json("run/revision.json", { pr = "owner/repo/123", head = string.rep("a", 40) })
    assert_failure(link, source_path, "Cited commit or file unavailable")
    write_json("run/revision.json", { pr = "other/repo/123", head = commit })
    assert_failure(link, source_path, "No cited commit")
    assert_failure("concept://owner/repo/%2e%2e/secret", source_path, "Invalid concept path")
    assert_failure("concept://owner/repo/file#L0", source_path, "Unsupported concept anchor")

    -- Exercise the wrapper with real Markdown parsing and asynchronous focus changes.
    local notifications = {}
    vim.notify = function(message)
        table.insert(notifications, message)
    end
    vim.cmd.edit(source_path)
    vim.bo.filetype = "markdown"
    local source_bufnr = vim.api.nvim_get_current_buf()
    local pending_handler
    local client = {
        name = "marksman",
        offset_encoding = "utf-16",
        handlers = {},
        request = function(_, _, _, handler)
            pending_handler = handler
            return true, 42
        end,
    }
    require("config.lsp.markdown").attach_definition_fallback(client)
    local received_result
    local function request(line_number)
        client:request("textDocument/definition", {
            textDocument = { uri = vim.uri_from_fname(source_path) },
            position = { line = line_number, character = 2 },
        }, function(_, result)
            received_result = result
        end, source_bufnr)
    end
    request(1)
    local marksman_location = { uri = vim.uri_from_fname(source_path) }
    pending_handler(nil, { marksman_location }, {})
    assert(received_result[1] == marksman_location and #notifications == 0)
    request(1)
    pending_handler(nil, nil, {})
    assert(#notifications == 1 and notifications[1]:find("Unknown repository key", 1, true))
    request(1)
    pending_handler({ code = -32800 }, nil, {})
    assert(#notifications == 1, "reported fallback errors for cancelled request")
    write_json("run/revision.json", { pr = "owner/repo/123", head = commit })
    write_json("run/revision.json", { pr = "owner/repo/123", head = string.rep("a", 40) })
    request(0)
    pending_handler(nil, nil, {})
    assert(
        #notifications == 2 and notifications[2]:find("Cited commit or file unavailable", 1, true)
    )
    write_json("run/revision.json", { pr = "owner/repo/123", head = commit })
    request(0)
    vim.cmd.enew()
    pending_handler(nil, {}, {})
    assert(received_result[1].uri == historical_location.uri)
    vim.api.nvim_set_current_buf(source_bufnr)
    assert(vim.lsp.util.show_document(received_result[1], "utf-16", { focus = true }))
    assert(vim.api.nvim_get_current_line() == "return 42")
end, debug.traceback)
vim.env.HOME = original_home
vim.notify = original_notify
vim.fn.delete(fixture_root, "rf")
assert(succeeded, failure)
print("Concept link resolver checks passed")
