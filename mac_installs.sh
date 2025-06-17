### NOTE: RUN THIS AFTER `setup.sh`

mkdir -p ~/.local/bin

# Detect CPU architecture and install accordingly
if [[ $(uname -m) == "arm64" ]]; then
    echo "Detected Apple Silicon (ARM) architecture"

    # Install homebrew if not already installed
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew for ARM..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo "Homebrew is already installed."
    fi
    grep -qxF 'eval "$(/opt/homebrew/bin/brew shellenv)"' ~/.zshrc || echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc

    # Neovim for ARM
    if [ ! -d "/opt/nvim-macos-arm64" ]; then
        echo "Installing Neovim for ARM..."
        pushd ~/
        curl -LO https://github.com/neovim/neovim/releases/download/nightly/nvim-macos-arm64.tar.gz
        sudo rm -rf /opt/nvim
        sudo tar xzf nvim-macos-arm64.tar.gz -C /opt
        rm nvim-macos-arm64.tar.gz
        popd
    else
        echo "Neovim is already installed."
    fi
    grep -qxF 'export PATH="$PATH:/opt/nvim-macos-arm64/bin"' ~/.zshrc || echo 'export PATH="$PATH:/opt/nvim-macos-arm64/bin"' >> ~/.zshrc
else
    echo "Detected Intel architecture"

    # Install homebrew if not already installed
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew for Intel..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        eval "$(/usr/local/bin/brew shellenv)"
    else
        echo "Homebrew is already installed."
    fi
    grep -qxF 'eval "$(/usr/local/bin/brew shellenv)"' ~/.zshrc || echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zshrc

    # Neovim for Intel
    if [ ! -d "/opt/nvim-macos-x86_64" ]; then
        echo "Installing Neovim for Intel..."
        pushd ~/
        curl -LO https://github.com/neovim/neovim/releases/download/nightly/nvim-macos-x86_64.tar.gz
        sudo rm -rf /opt/nvim
        sudo tar xzf nvim-macos-x86_64.tar.gz -C /opt
        rm nvim-macos-x86_64.tar.gz
        popd
    else
        echo "Neovim is already installed."
    fi
    grep -qxF 'export PATH="$PATH:/opt/nvim-macos-x86_64/bin"' ~/.zshrc || echo 'export PATH="$PATH:/opt/nvim-macos-x86_64/bin"' >> ~/.zshrc
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

# rsync
if ! command -v rsync &> /dev/null; then
    echo "Installing rsync..."
    brew install rsync
else
    echo "rsync is already installed."
fi

# wget
if ! command -v wget &> /dev/null; then
    echo "Installing wget..."
    brew install wget
else
    echo "wget is already installed."
fi

# uv
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
else
    echo "uv is already installed."
fi


# fnm
if ! command -v fnm &> /dev/null; then
    echo "Installing fnm..."
    # this uses homebrew anyways????
    curl -fsSL https://fnm.vercel.app/install | bash -s -- --skip-shell
else
    echo "fnm is already installed."
fi
grep -qxF 'eval "$(fnm env --use-on-cd shell zsh)"' ~/.zshrc || echo 'eval "$(fnm env --use-on-cd --shell zsh)"' >> ~/.zshrc
eval "$(fnm env --use-on-cd shell zsh)"

# pnpm
if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    brew install pnpm
else
    echo "pnpm is already installed."
fi

if ! command -v spoof &> /dev/null; then
    echo "Installing spoof..."
    pnpm install -g spoof
else
    echo "pnpm is already installed."
fi


# Oh-my-zsh
if [ ! -d ~/.oh-my-zsh ]; then
    echo "Installing Oh-my-zsh..."
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --keep-zshrc --unattended
else
    echo "Oh-my-zsh is already installed."
fi

defaults write -g ApplePressAndHoldEnabled -bool false

echo "Script completed. Please restart your terminal or run 'source ~/.zshrc' to apply changes."
