-- Run from the repo root: nvim --headless -u NONE -i NONE -l nvim_config/tests/markdown_links.lua
vim.opt.runtimepath:prepend(vim.fn.getcwd() .. "/nvim_config")
vim.opt.runtimepath:append(vim.fn.stdpath("data") .. "/site")
vim.opt.runtimepath:append(vim.fn.stdpath("data") .. "/lazy/nvim-treesitter")

local fixture_lines = {
    "[concept](/learning/concepts/transactions.md)",
    "[sibling](isolation.md#guarantees)",
    "[source](/repo/access.ts#L23)",
    "[relative source](../../repo/main.py)",
    "[file URI](file:///repo/main.rs#L1)",
    "[encoded](../concepts/space%20name.markdown#heading)",
    "[angle](</learning/concepts/space name.md>)",
    "[website](https://example.com/concepts/test.md)",
    "[remote code](https://github.com/user/repo/main.ts)",
    "[document](../README.md)",
    "[config](/repo/settings.json)",
    "`[inline code](/repo/main.ts)`",
    "![image](/repo/image.ts)",
}
local fixture_bufnr = vim.api.nvim_create_buf(false, true)
vim.api.nvim_buf_set_name(fixture_bufnr, "/learning/concepts/current.md")
vim.api.nvim_buf_set_lines(fixture_bufnr, 0, -1, false, fixture_lines)
local fixture_parser = vim.treesitter.get_parser(fixture_bufnr, "markdown")
fixture_parser:parse(true)
local rendered_marks = {}
fixture_parser:for_each_tree(function(syntax_tree, language_tree)
    if language_tree:lang() == "markdown_inline" then
        local parsed_marks = require("config.markdown_links").parse({
            buf = fixture_bufnr,
            root = syntax_tree:root(),
        })
        for _, link_mark in ipairs(parsed_marks) do
            rendered_marks[link_mark.start_row + 1] = link_mark
            -- Exercise Neovim's extmark contract as the rendering plugin does.
            vim.api.nvim_buf_set_extmark(
                fixture_bufnr,
                vim.api.nvim_create_namespace("markdown-link-test"),
                link_mark.start_row,
                link_mark.start_col,
                link_mark.opts
            )
        end
    end
end)
for fixture_index = 1, #fixture_lines do
    local expected_highlight
    if fixture_index <= 2 or fixture_index == 6 or fixture_index == 7 then
        expected_highlight = "RenderMarkdownConceptLink"
    elseif fixture_index <= 5 then
        expected_highlight = "RenderMarkdownCodeLink"
    end
    local link_mark = rendered_marks[fixture_index]
    assert(
        (link_mark and link_mark.opts.hl_group) == expected_highlight,
        "Unexpected link classification: " .. fixture_lines[fixture_index]
    )
    if link_mark then
        assert(link_mark.start_col == 1, "Highlight must start at the visible label")
        assert(fixture_lines[fixture_index]:sub(link_mark.opts.end_col + 1, link_mark.opts.end_col + 1) == "]")
    end
end
print("Markdown link rendering checks passed")
vim.cmd.quit()
