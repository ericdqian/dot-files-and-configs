# dot-files-and-configs

## How this works

`zsh_config/device_specific_zsh_config` is symlinked to the system's `~/.zshrc`. This way, any new installations that modify the `.zshrc` are localized. `zsh_config/device_specific_zsh_config` is gitignored, and only the line sourcing `~/.general_zsh_config` should be kept.

`zsh_config/general_zsh_config` is symlinked to the system's `~/.general_zsh_config` and sourced from `~/.zsh_config/device_specific_zsh_config`.

`AGENTS.md` is symlinked into `~/.codex/AGENTS.md` and `~/.claude/CLAUDE.md`.

Global agent skills live in `dot-agents/skills`. `setup.sh` symlinks that directory to `~/.agents/skills` for Codex and `~/.claude/skills` for Claude Code. For example, `address-pr-feedback` is available as `$address-pr-feedback` in Codex and `/address-pr-feedback` in Claude Code.

## A note on dependencies

Mason will require a few things like unzip, npm, and pip to be available in order to properly install the language servers. If you see any issues with the installation, make sure that the above are available in your path.

## Terminal

### Karabiner-Elements

`mac_installs.sh` installs Karabiner-Elements, and `setup.sh` symlinks this repository's Option-F/B word-navigation rule into Karabiner's complex-modification assets. After the initial installation, grant Karabiner the macOS permissions it requests, then enable **Option-F/B move forward/backward by word** from **Complex Modifications**. It maps Option-F to Option-Right Arrow and Option-B to Option-Left Arrow, so native apps, Chrome, and terminals receive their normal word-navigation input.

If Karabiner cannot connect to `karabiner_console_user_server`, or macOS has not recognized a permission change:

1. In **System Settings → General → Login Items & Extensions**, turn **Karabiner-Elements Non-Privileged Agents v2** off, wait a few seconds, then turn it on again.
2. Quit and reopen Karabiner-Elements. You can also restart it from the menu bar or Settings, or run:

   ```sh
   launchctl kickstart -k gui/$(id -u)/org.pqrs.service.agent.karabiner_console_user_server
   ```

3. If the Accessibility entry is missing, open **System Settings → Privacy & Security → Accessibility**, click **+**, press **Command-Shift-G**, and add:

   ```text
   /Library/Application Support/org.pqrs/Karabiner-Elements/Karabiner-Core-Service.app
   ```

4. Restart the Mac if Karabiner still cannot connect or macOS still does not recognize the permissions after the agent and app restart.

See Karabiner's [restart instructions](https://karabiner-elements.pqrs.org/docs/manual/operation/restart/) and [required macOS settings](https://karabiner-elements.pqrs.org/docs/manual/misc/required-macos-settings/) for more detail.

### Kitty

```
curl -L https://sw.kovidgoyal.net/kitty/installer.sh | sh /dev/stdin
```

## Zsh setup

### Oh-my-zsh

```
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --keep-zshrc
```

### Neovim

```
curl -LO --output-dir ~/ https://github.com/neovim/neovim/releases/download/nightly/nvim-macos.tar.gz
tar xzf ~/nvim-macos.tar.gz
```

### Powerlevel10k

```
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ~/powerlevel10k
```

### fzf

```
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install
```

### nvm

```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.2/install.sh | bash
```

### miniconda

Instructions here download the Mac package; adjust this to your installation

```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -O miniconda.sh

bash miniconda.sh -b -p $HOME/miniconda && rm miniconda.sh
```

### bat

```
brew install bat
```

### zsh highlighting

```
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ~/.zsh-syntax-highlighting
```

### ripgrep

This replaces `grep` and is also used by `fzf` in neovim

```
brew install ripgrep
```

### Kubernetes

Follow the instructions here depending on device type: https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/

### k9s

```
brew install derailed/k9s/k9s
```

## Additional installations

Check the lsp and null-ls files for neovim. Languages servers and other linters/formatters may be needed
