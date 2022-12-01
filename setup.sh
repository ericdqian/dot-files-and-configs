CUR_DIR=$(pwd)
echo Symlinking configs at $CUR_DIR
ln -s ${CUR_DIR}/zsh_config/.zshrc ~/.zshrc
ln -s ${CUR_DIR}/nvim_config ~/.config/nvim
