runtime basic.vim
runtime extended.vim
runtime other.vim
if exists('g:vscode')

else
    lua require('plugins')
endif
