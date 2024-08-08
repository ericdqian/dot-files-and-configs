### NOTE: RUN THIS AFTER `setup.sh`

mkdir -p ~/.local/bin

# Install homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
grep -qxF 'eval "$(/opt/homebrew/bin/brew shellenv)"' ~/.zshrc || echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc


# Neovim
pushd ~/
curl -LO https://github.com/neovim/neovim/releases/download/nightly/nvim-macos-x86_64.tar.gz
sudo rm -rf /opt/nvim
sudo tar xzf nvim-macos-x86_64.tar.gz -C /opt
popd

grep -qxF 'export PATH="$PATH:/opt/nvim-macos-x86_64/bin"' ~/.zshrc || echo 'export PATH="$PATH:/opt/nvim-macos-x86_64/bin"' >> ~/.zshrc

# Powerlink
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ~/powerlevel10k

# TODO: link .p10k

# FZF
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install --no-update-rc --completion --key-bindings

# bat
brew install bat

# zsh highlighting
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ~/zsh-syntax-highlighting

# ripgrep
brew install ripgrep

#k9s
brew install derailed/k9s/k9s

# # Install Poetry
# curl -sSL https://install.python-poetry.org | POETRY_HOME=~/.bin/poetry python3

# Oh-my-zsh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --keep-zshrc
