### NOTE: RUN THIS AFTER `setup.sh`

# zsh
sudo apt install zsh

# Oh-my-zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# gcc
sudo apt install build-essential

# Neovim
pushd ~/
curl -LO https://github.com/neovim/neovim/releases/download/v0.9.1/nvim-linux64.tar.gz
sudo rm -rf /opt/nvim
sudo tar -C /opt -xzf nvim-linux64.tar.gz
popd

grep -qxF 'export PATH="$PATH:/opt/nvim-linux64/bin"' ~/.zshrc || echo 'export PATH="$PATH:/opt/nvim-linux64/bin"' >> ~/.zshrc

# Powerlink
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ~/powerlevel10k

# FZF
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install

# bat
sudo apt install bat
# https://github.com/sharkdp/bat/issues/982
mkdir -p ~/.local/bin
ln -s /usr/bin/batcat ~/.local/bin/bat

# zsh highlighting
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git /usr/share/zsh-syntax-highlighting
echo "source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" >> ${ZDOTDIR:-$HOME}/.zshrc

# ripgrep
sudo apt-get install ripgrep

