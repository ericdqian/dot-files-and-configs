runtime basic.vim
runtime extended.vim
runtime other.vim
lua require('plugins')
if exists('g:vscode')
    lua require('vscode-bindings')
endif
