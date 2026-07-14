CUR_DIR=$(pwd)
echo Symlinking configs at $CUR_DIR

link_file() {
    SOURCE=$1
    TARGET=$2
    DESCRIPTION=$3

    if [[ -L $TARGET && $(readlink "$TARGET") == "$SOURCE" ]]; then
        echo "Not creating new $DESCRIPTION because $TARGET is already symlinked"
    elif [[ -e $TARGET || -L $TARGET ]]; then
        echo "Not linking $DESCRIPTION because $TARGET already exists and is not the expected symlink"
    else
        echo "Linking $DESCRIPTION"
        ln -s "$SOURCE" "$TARGET"
    fi
}

if [[ -L ~/.general_zsh_config ]]; then
    echo "Not creating new general zsh config because ~/.general_zsh_config is already symlinked"
else
    echo "Linking general zsh config"
    ln -s ${CUR_DIR}/zsh_config/general_zsh_config ~/.general_zsh_config
fi
if [[ -L ~/.zshrc ]]; then
    echo "Not creating new zshrc file because ~/.zshrc is already symlinked"
else
    UNIQUE_SUFFIX=$(dd if=/dev/urandom bs=16 count=1 2>/dev/null | base64 | tr -dc 'A-Za-z0-9' | head -c 16)
    echo "Creating new zshrc file with suffix $UNIQUE_SUFFIX"
    cp ${CUR_DIR}/zsh_config/device_specific_zsh_config ${CUR_DIR}/zsh_config/zshrc_${UNIQUE_SUFFIX}
    ln -s ${CUR_DIR}/zsh_config/zshrc_${UNIQUE_SUFFIX} ~/.zshrc
fi
# TODO: backup and overwrite ~/.config/nvim if it already exists so the symlink is created properly instead of making nvim_config inside of ~/.config/nvim
mkdir -p ~/.config
# Link nvim if not already linked
if [[ -L ~/.config/nvim ]]; then
    echo "Not creating new nvim config because ~/.config/nvim is already symlinked"
else
    echo "Linking nvim config"
    ln -s ${CUR_DIR}/nvim_config ~/.config/nvim
fi
mkdir -p ~/.config/kitty
if [[ -L ~/.config/kitty/kitty.conf ]]; then
    echo "Not creating new kitty config because ~/.config/kitty/kitty.conf is already symlinked"
else
    echo "Linking kitty config"
    ln -s ${CUR_DIR}/kitty_config/kitty.conf ~/.config/kitty/kitty.conf
fi
mkdir -p ~/.config/wezterm
if [[ -L ~/.config/wezterm/wezterm.lua ]]; then
    echo "Not creating new wezterm config because ~/.config/wezterm/wezterm.lua is already symlinked"
else
    echo "Linking wezterm config"
    ln -s ${CUR_DIR}/wezterm_config/.wezterm.lua ~/.config/wezterm/wezterm.lua
fi
link_file "${CUR_DIR}/tmux_config/.tmux.conf" ~/.tmux.conf "tmux config"
mkdir -p ~/.config/karabiner/assets/complex_modifications
link_file "${CUR_DIR}/karabiner_config/option_word_navigation.json" ~/.config/karabiner/assets/complex_modifications/option_word_navigation.json "Karabiner Option-F/B word navigation rule"
mkdir -p ~/.codex ~/.claude
link_file "${CUR_DIR}/AGENTS.md" ~/.codex/AGENTS.md "Codex agents config"
link_file "${CUR_DIR}/AGENTS.md" ~/.claude/CLAUDE.md "Claude agents config"
link_file "${CUR_DIR}/claude_config/settings.json" ~/.claude/settings.json "Claude settings"
link_file "${CUR_DIR}/claude_config/statusline.sh" ~/.claude/statusline.sh "Claude status line script"
# Codex shared config lives at the system level (/etc/codex/config.toml) so it
# layers underneath ~/.codex/config.toml, which stays a real, local-only file
# holding machine-specific paths and app-managed state. See AGENTS.md.
sudo mkdir -p /etc/codex
if [[ -L /etc/codex/config.toml && $(readlink /etc/codex/config.toml) == "${CUR_DIR}/codex_config/config.toml" ]]; then
    echo "Not creating new Codex shared config because /etc/codex/config.toml is already symlinked"
elif [[ -e /etc/codex/config.toml || -L /etc/codex/config.toml ]]; then
    echo "Not linking Codex shared config because /etc/codex/config.toml already exists and is not the expected symlink"
else
    echo "Linking Codex shared config (requires sudo)"
    sudo ln -s "${CUR_DIR}/codex_config/config.toml" /etc/codex/config.toml
fi
mkdir -p ~/.agents
link_file "${CUR_DIR}/dot-agents/skills" ~/.agents/skills "global agent skills"
link_file "${CUR_DIR}/dot-agents/skills" ~/.claude/skills "Claude skills"
#
# # Ignore future updates to zsh_config/device_specific_zsh_config
# git update-index --assume-unchanged ./zsh_config/device_specific_zsh_config

git config --global core.editor "nvim"
git config --global push.autoSetupRemote true

# Prompt name and email to use for git if not already set
if [[ -z $(git config --global user.name) ]]; then
    echo "Enter your name for git: "
    read NAME
    git config --global user.name $NAME
fi
if [[ -z $(git config --global user.email) ]]; then
    echo "Enter your email for git: "
    read EMAIL
    git config --global user.email $EMAIL
fi
