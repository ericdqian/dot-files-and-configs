set number 
set relativenumber

set mouse=n

autocmd Filetype javascript setlocal ts=2 sts=2 sw=2
autocmd Filetype typescript setlocal ts=2 sts=2 sw=2
autocmd Filetype typescriptreact setlocal ts=2 sts=2 sw=2
autocmd Filetype html setlocal ts=2 sts=2 sw=2
autocmd Filetype swift setlocal ts=2 sts=2 sw=2

" Allows for opt+backspace to delete a word
inoremap <A-BS> <C-w>

" Copy to clipboard
vnoremap  <leader>y  "+y
nnoremap  <leader>y  "+y

" Paste from clipboard
nnoremap <leader>p "+p
vnoremap <leader>p "+p

