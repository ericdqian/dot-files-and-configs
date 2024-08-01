### NOTE: RUN THIS AFTER `setup.sh`

sudo apt update

# gcc
sudo apt install build-essential

# required for Mason to install stuff
sudo apt install npm
sudo apt install unzip

# requierd for copilot
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install 20


mkdir -p ~/.local/bin

# zsh
sudo apt install zsh

# Neovim
pushd ~/
curl -LO https://github.com/neovim/neovim/releases/download/v0.9.1/nvim-linux64.tar.gz
sudo rm -rf /opt/nvim
sudo tar -C /opt -xzf nvim-linux64.tar.gz
popd

grep -qxF 'export PATH="$PATH:/opt/nvim-linux64/bin"' ~/.zshrc || echo 'export PATH="$PATH:/opt/nvim-linux64/bin"' >> ~/.zshrc

# Powerlink
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ~/powerlevel10k

# TODO: link .p10k

# FZF
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install --no-update-rc --completion --key-bindings

# bat
sudo apt install bat
# https://github.com/sharkdp/bat/issues/982
ln -s /usr/bin/batcat ~/.local/bin/bat

# zsh highlighting
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ~/zsh-syntax-highlighting

# ripgrep
sudo apt-get install ripgrep

# Oh-my-zsh
# Keep oh-my-zsh last since if it runs zsh (controlled by RUNZSH), then it will stop the rest of the installation in this script
if [[ "$SHELL" == */zsh ]]; then
    export RUNZSH="no"
fi
export KEEP_ZSHRC="yes"
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
