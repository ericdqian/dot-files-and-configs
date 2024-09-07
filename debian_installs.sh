### NOTE: RUN THIS AFTER `setup.sh`

sudo apt update

# gcc
sudo apt install build-essential

# required for Mason to install stuff
sudo apt install npm
sudo apt install unzip

# requierd for copilot
# NVM (Node Version Manager)
if [ ! -d "$HOME/.nvm" ]; then
    echo "Installing NVM..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm

    if command -v nvm &> /dev/null; then
        echo "Installing Node.js v20..."
        nvm install 20
    else
        echo "NVM installation failed. Please check and retry."
    fi
else
    echo "NVM is already installed."
fi

# Create .local/bin directory
mkdir -p ~/.local/bin

# zsh
if ! command -v zsh &> /dev/null; then
    echo "Installing zsh..."
    sudo apt install zsh -y
else
    echo "zsh is already installed."
fi

# Neovim
if [ ! -d "/opt/nvim-linux64" ]; then
    echo "Installing Neovim..."
    pushd ~/
    curl -LO https://github.com/neovim/neovim/releases/download/v0.9.1/nvim-linux64.tar.gz
    sudo rm -rf /opt/nvim
    sudo tar -C /opt -xzf nvim-linux64.tar.gz
    rm nvim-linux64.tar.gz
    popd
    grep -qxF 'export PATH="$PATH:/opt/nvim-linux64/bin"' ~/.zshrc || echo 'export PATH="$PATH:/opt/nvim-linux64/bin"' >> ~/.zshrc
else
    echo "Neovim is already installed."
fi

# Powerlevel10k
if [ ! -d ~/powerlevel10k ]; then
    echo "Installing Powerlevel10k..."
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ~/powerlevel10k
else
    echo "Powerlevel10k is already installed."
fi
# TODO: link .p10k

# FZF
if [ ! -d ~/.fzf ]; then
    echo "Installing FZF..."
    git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
    ~/.fzf/install --no-update-rc --completion --key-bindings
else
    echo "FZF is already installed."
fi

# bat
if ! command -v bat &> /dev/null; then
    echo "Installing bat..."
    sudo apt install bat -y
    # https://github.com/sharkdp/bat/issues/982
    ln -s /usr/bin/batcat ~/.local/bin/bat
else
    echo "bat is already installed."
fi

# zsh highlighting
if [ ! -d ~/zsh-syntax-highlighting ]; then
    echo "Installing zsh-syntax-highlighting..."
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ~/zsh-syntax-highlighting
else
    echo "zsh-syntax-highlighting is already installed."
fi

# ripgrep
if ! command -v rg &> /dev/null; then
    echo "Installing ripgrep..."
    sudo apt-get install ripgrep -y
else
    echo "ripgrep is already installed."
fi

# Oh-my-zsh
if [ ! -d ~/.oh-my-zsh ]; then
    echo "Installing Oh-my-zsh..."
    # Keep oh-my-zsh last since if it runs zsh (controlled by RUNZSH), then it will stop the rest of the installation in this script
    if [[ "$SHELL" == */zsh ]]; then
        export RUNZSH="no"
    fi
    export KEEP_ZSHRC="yes"
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
else
    echo "Oh-my-zsh is already installed."
fi

echo "Script completed. Please restart your terminal or run 'source ~/.zshrc' to apply changes."
