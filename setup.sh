CUR_DIR=$(pwd)
echo Symlinking configs at $CUR_DIR
ln -s ${CUR_DIR}/zsh_config/.zshrc ~/.zshrc
mkdir -p ~/.config/nvim
ln -s ${CUR_DIR}/nvim_config ~/.config/nvim
mkdir -p ~/.config/kitty
ln -s ${CUR_DIR}/kitty_config/kitty.conf ~/.config/kitty/kitty.conf
mkdir -p ~/.config/wezterm
ln -s ${CUR_DIR}/wezterm_config/.wezterm.lua ~/.config/wezterm/wezterm.lua
