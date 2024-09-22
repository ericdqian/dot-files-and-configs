CUR_DIR=$(pwd)
echo Symlinking configs at $CUR_DIR
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
#
# # Ignore future updates to zsh_config/device_specific_zsh_config
# git update-index --assume-unchanged ./zsh_config/device_specific_zsh_config
