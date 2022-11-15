## Set up Powerlevel10k

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi
if [[ -f ~/powerlevel10k/powerlevel10k.zsh-theme ]]; then source ~/powerlevel10k/powerlevel10k.zsh-theme; else echo Powerlevel10k not installed... please follow README instructions to install or; fi
# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

## Set up fzf
if [ -f ~/.fzf.zsh ]; then source ~/.fzf.zsh; else echo Fzf not installed... please follow README instructions to install; fi

## Set up nvm
export NVM_DIR=~/.nvm
if [ -s "$NVM_DIR/nvm.sh" ]; then \. "$NVM_DIR/nvm.sh"; else echo nvm not installed... please follow README instructions to install; fi

## Set up miniconda
__conda_setup="$(~/miniconda/bin/conda 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f ~/miniconda/etc/profile.d/conda.sh ]; then
        . ~/miniconda/etc/profile.d/conda.sh
    else
        export PATH="$HOME/miniconda/bin:$PATH"
    fi
fi
unset __conda_setup

## Import aliases
CONFIG_ZSHRC_PATH=$(readlink -f ~/.zshrc)
DOTFILE_CONFIG_PATH=$(dirname $CONFIG_ZSHRC_PATH)
for filename in ${DOTFILE_CONFIG_PATH}/zsh_config/aliases/*; do
  source $filename
done



