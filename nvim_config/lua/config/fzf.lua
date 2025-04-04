local M = {}

-- Can use bat to do syntax highlighting
-- brew install bat
function M.setup()
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
