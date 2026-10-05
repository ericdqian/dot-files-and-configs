local M = {}

-- Can use bat to do syntax highlighting
-- brew install bat
function M.setup()
    vim.g.fzf_history_dir = vim.fn.stdpath("data") .. "/fzf-history"
    -- Keep file navigation on Ctrl-P/N while history uses Alt-P/N.
    vim.g.fzf_vim = {
        options = "--bind=ctrl-p:up-match,ctrl-n:down-match,alt-p:prev-history,alt-n:next-history",
    }

    vim.cmd([[
        let g:fzf_layout = { 'window': { 'width': 0.95, 'height': 0.95 } }
        function! RipgrepFzf(query, fullscreen)
          let command_fmt = 'rg --column --line-number --no-heading --color=always --smart-case -- %s || true'
          let initial_command = printf(command_fmt, shellescape(a:query))
          let reload_command = printf(command_fmt, '{q}')
          let spec = {'options': ['--phony', '--query', a:query, '--bind', 'change:reload:'.reload_command]}
          call fzf#vim#grep(initial_command, 1, fzf#vim#with_preview(spec), a:fullscreen)
        endfunction
        command! -nargs=* -bang RG call RipgrepFzf(<q-args>, <bang>0)
        nmap ; :Buffers<CR>
        nmap <Leader>a :RG<CR>
        nmap <Leader>z :Files<CR>
        nmap <Leader>t :GFiles<CR>
    ]])
end

return M
