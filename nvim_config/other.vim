" This file is for custom mappings
set number 
set relativenumber

set mouse=n

" Only show winbar with tabs if there is >1 tab
set showtabline=1

" Spacing
autocmd Filetype javascript setlocal ts=2 sts=2 sw=2
autocmd Filetype typescript setlocal ts=2 sts=2 sw=2
autocmd Filetype typescriptreact setlocal ts=2 sts=2 sw=2
autocmd Filetype html setlocal ts=2 sts=2 sw=2
autocmd Filetype swift setlocal ts=2 sts=2 sw=2
autocmd Filetype swift setlocal ts=4 sts=4 sw=4

" Allows for opt+backspace to delete a word
inoremap <A-BS> <C-w>

" Copy to clipboard
vnoremap  <leader>y  "+y
nnoremap  <leader>y  "+y

" Paste from clipboard
nnoremap <leader>p "+p
vnoremap <leader>p "+p


" Don't auto-continue comments
autocmd BufNewFile,BufRead * setlocal formatoptions-=cro


" For long lines that soft wrap, make j and k behave as they were different lines but have expressions respect line numbers
noremap j gj  
noremap k gk 
noremap <expr> j v:count ? 'j' : 'gj'
noremap <expr> k v:count ? 'k' : 'gk'

" Map so , advances a search from f/t/F/T and < goes backwards
function! s:MapCommaOrUnindent() abort
  if mode() !=# 'v' || col('.') == 1
    return '<'
  else
    return ','
  endif
endfunction

nnoremap , ;
vnoremap , ;
nnoremap < ,
vnoremap <expr> < <SID>MapCommaOrUnindent()

" Map to change inner parens
onoremap in( :<c-u>normal! f(vi(<cr>
onoremap ip( :<c-u>normal! F(vi(<cr>


" Map ctrl+L to ctrl+P in netrw so window navigation can be used
augroup netrw_mapping
  autocmd!
  autocmd filetype netrw call NetrwMapping()
augroup END

function! NetrwMapping()
  " TODO: make sure that that this ctrl+P works properly
  nnoremap <silent> <buffer> <c-p> :e .
  nnoremap <silent> <buffer> <c-l> <c-w>l
endfunction

" Line numbers in netrw
let g:netrw_bufsettings = 'noma nomod nu nowrap ro nobl'

nnoremap <A-h> <C-w><
nnoremap <A-l> <C-w>>
nnoremap <A-j> <C-w>-
nnoremap <A-k> <C-w>+
