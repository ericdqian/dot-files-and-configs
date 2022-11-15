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

## Import aliases
CONFIG_ZSHRC_PATH=$(readlink -f ~/.zshrc)
DOTFILE_CONFIG_PATH=$(dirname $CONFIG_ZSHRC_PATH)
for filename in ${DOTFILE_CONFIG_PATH}/zsh_config/aliases/*; do
  source $filename
done

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/ericqian/opt/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/ericqian/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/ericqian/opt/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/ericqian/opt/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<


export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
