runtime basic.vim
runtime extended.vim
runtime other.vim
lua require('plugins')
if exists('g:vscode')
    set cmdheight=4 "prevent vscode-neovim messages from popping up messages
    lua require('vscode-bindings')
endif
