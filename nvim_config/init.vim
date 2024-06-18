runtime basic.vim
runtime extended.vim
runtime other.vim
if exists('g:vscode')
    lua require('vscode-bindings')
else
    lua require('plugins')
endif
