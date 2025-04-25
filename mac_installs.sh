### NOTE: RUN THIS AFTER `setup.sh`

mkdir -p ~/.local/bin

# Detect CPU architecture and install accordingly
if [[ $(uname -m) == "arm64" ]]; then
    echo "Detected Apple Silicon (ARM) architecture"
    
    # Install homebrew if not already installed
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew for ARM..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        grep -qxF 'eval "$(/opt/homebrew/bin/brew shellenv)"' ~/.zshrc || echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
    else
        echo "Homebrew is already installed."
    fi

    # Neovim for ARM
    if [ ! -d "/opt/nvim-macos-arm64" ]; then
        echo "Installing Neovim for ARM..."
        pushd ~/
        curl -LO https://github.com/neovim/neovim/releases/download/nightly/nvim-macos-arm64.tar.gz
        sudo rm -rf /opt/nvim
        sudo tar xzf nvim-macos-arm64.tar.gz -C /opt
        rm nvim-macos-arm64.tar.gz
        popd
        grep -qxF 'export PATH="$PATH:/opt/nvim-macos-arm64/bin"' ~/.zshrc || echo 'export PATH="$PATH:/opt/nvim-macos-arm64/bin"' >> ~/.zshrc
    else
        echo "Neovim is already installed."
    fi
else
    echo "Detected Intel architecture"
    
    # Install homebrew if not already installed
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew for Intel..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        grep -qxF 'eval "$(/usr/local/bin/brew shellenv)"' ~/.zshrc || echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zshrc
    else
        echo "Homebrew is already installed."
    fi

    # Neovim for Intel
    if [ ! -d "/opt/nvim-macos-x86_64" ]; then
        echo "Installing Neovim for Intel..."
        pushd ~/
        curl -LO https://github.com/neovim/neovim/releases/download/nightly/nvim-macos-x86_64.tar.gz
        sudo rm -rf /opt/nvim
        sudo tar xzf nvim-macos-x86_64.tar.gz -C /opt
        rm nvim-macos-x86_64.tar.gz
        popd
        grep -qxF 'export PATH="$PATH:/opt/nvim-macos-x86_64/bin"' ~/.zshrc || echo 'export PATH="$PATH:/opt/nvim-macos-x86_64/bin"' >> ~/.zshrc
    else
        echo "Neovim is already installed."
    fi
fi

# Powerlink
if [ ! -d ~/powerlevel10k ]; then
    echo "Installing Powerlevel10k..."
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ~/powerlevel10k
else
    echo "Powerlevel10k is already installed."
fi
# TODO: link .p10k

# FZF
if [ ! -d ~/.fzf ]; then
    # https://github.com/junegunn/fzf?tab=readme-ov-file#upgrading-fzf
    echo "Installing FZF..."
    git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
    ~/.fzf/install --no-update-rc --completion --key-bindings
else
    echo "FZF is already installed."
fi

# bat
if ! command -v bat &> /dev/null; then
    echo "Installing bat..."
    brew install bat
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
    brew install ripgrep
else
    echo "ripgrep is already installed."
fi

# k9s
if ! command -v k9s &> /dev/null; then
    echo "Installing k9s..."
    brew install derailed/k9s/k9s
else
    echo "k9s is already installed."
fi

# Oh-my-zsh
if [ ! -d ~/.oh-my-zsh ]; then
    echo "Installing Oh-my-zsh..."
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --keep-zshrc
else
    echo "Oh-my-zsh is already installed."
fi

defaults write -g ApplePressAndHoldEnabled -bool false

echo "Script completed. Please restart your terminal or run 'source ~/.zshrc' to apply changes."
