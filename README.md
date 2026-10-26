# dot-files-and-configs

## How this works

`zsh_config/device_specific_zsh_config` is symlinked to the system's `~/.zshrc`. This way, any new installations that modify the `.zshrc` are localized. `zsh_config/device_specific_zsh_config` is gitignored, and only the line sourcing `~/.general_zsh_config` should be kept.

`zsh_config/general_zsh_config` is symlinked to the system's `~/.general_zsh_config` and sourced from `~/.zsh_config/device_specific_zsh_config`.

`AGENTS.md` is symlinked into `~/.codex/AGENTS.md` and `~/.claude/CLAUDE.md`.

Global agent skills live in `dot-agents/skills`. `setup.sh` symlinks that directory to `~/.agents/skills` for Codex and `~/.claude/skills` for Claude Code. For example, `address-pr-feedback` is available as `$address-pr-feedback` in Codex and `/address-pr-feedback` in Claude Code.

`agent_notify/` makes a background coding agent noticeable when it finishes or blocks on input. `setup.sh` symlinks it to `~/.agent-notify`, and both agents call `agent_notify.sh` from their lifecycle hooks: Claude Code via the `hooks` block in `claude_config/settings.json`, Codex via `codex_config/hooks.json` symlinked to `~/.codex/hooks.json`. It surfaces three signals:

- **tmux footer** — an orange `!` marks a window whose agent needs input, a green `*` one that finished. The state is a per-window `@agent_state` option, so it disappears with the window rather than needing a state file to clean up.
- **WezTerm tab** — the same flag, aggregated across the windows of the session that tab shows, so the tab and the footer always agree. It is delivered by writing OSC 1337 straight to `#{client_tty}`, which deliberately bypasses tmux: tmux's own passthrough drops sequences emitted from a window that is not currently visible, which is exactly the case worth reporting.
- **macOS Dock** — `AgentAlert.app` bounces when an agent needs input, and re-bounces every few minutes while it stays blocked, so a first bounce that went unseen is not the only warning. WezTerm cannot request user attention for its own icon ([wezterm/wezterm#6183](https://github.com/wezterm/wezterm/issues/6183)), so the bounce necessarily comes from a small separate bundle and shows its own Dock item.

Markers retire themselves. A finished marker clears as soon as its window is looked at, driven by tmux's `pane-focus-in` hook, which covers both switching to a window and WezTerm regaining focus. A waiting marker is deliberately kept until the agent is answered, since that agent is still blocked and the footer would otherwise go quiet about it after a glance. A turn that finishes while its window is already on screen is never marked at all, and the Dock stays quiet while the blocked window is the one being viewed.

Only windows in an attached session are marked. A window nobody is attached to cannot be looked at, so a marker there would sit in a count that nothing can ever clear — on a machine running background review agents in detached sessions, that is most of them. Such an agent still bounces the Dock if it blocks, since that needs answering wherever it runs, though with no marker to track it there is nothing to re-bounce from.

Two cases need more than that, because neither agent reports them. No hook fires when a permission is *approved*, so a waiting marker would outlive the block and be re-bounced at for the rest of the turn; `PostToolUse` stands in, since a tool that has run proves the approval happened. That hook fires on every tool call; after recording the observed branch, the handler skips notification work when the marker is unchanged. And a session killed hard never fires `SessionEnd`, so the re-bounce supervisor drops markers from windows whose panes have all fallen back to a shell — asking whether a window still runs *anything*, rather than matching agent process names, which for Claude Code is its version number.

## Worktree navigation

`cwt` switches to an existing worktree by path or branch, or opens a fuzzy picker
when there is no exact match. It also accepts a PR number (`cwt 42`, `cwt '#42'`)
or URL (`cwt https://github.com/OWNER/REPO/pull/42`). PR lookup requires an
authenticated GitHub CLI (`gh`) and Python 3. It uses the shared `navigation/` PR
resolver to find an existing local worktree for the PR's head branch, and works
outside tmux too. URLs must belong to the current repository; PR lookup errors and
missing worktrees report an error. These commands do not create worktrees.
`ccwt` (Cursor) and `cnwt` (Neovim) accept the same arguments. You can also paste
PR numbers or full URLs into the picker after running any of these commands.
Interactive PR searches share tmux navigation's five-minute cache; explicit PR
arguments resolve a fresh head. Failed lookups stay visible in the picker and
are not cached. Clearing the PR query restores ordinary fuzzy filtering.

The top-level `navigation/` package owns GitHub resolution, repository identity,
PR caching, and the complete fzf picker flow: snapshots, query filtering, reloads,
and selection validation. Both shell worktree commands and
`tmux_config/navigation/search.py` use it. Tmux pane and window behavior stays
under `tmux_config/`. Script paths resolve installed symlinks back to this checkout,
so no Python package installation or `PYTHONPATH` configuration is needed.

## Claude session routing

Claude's `SessionStart` hook also runs `agent_notify/register_claude_session.sh`.
It atomically writes `{sessionId, messagingSocket}` to
`~/.local/state/coding-agents/claude-sessions/<session-id>.json` with mode 0600.
Set `CLAUDE_SESSION_REGISTRY_DIR` in both Claude's environment and the review
manager to override that directory. No messaging token is stored. The manager
uses commit prefixes such as `[claude SESSION_ID]` to find this local inbox.

Start or resume Claude after updating the hook to register its inbox. A session
without messaging support records an empty endpoint. Mappings remain after exit
and are refreshed on resume; the manager treats an absent socket as offline and
includes the target session ID in each message to reject reused socket paths.
Claude's normal inbound-message settings still apply. This registration is local
to the machine and user running the hook and review manager.

Validate the hook with `node --test agent_notify/register_claude_session.test.cjs`.

## A note on dependencies

Mason will require a few things like unzip, npm, and pip to be available in order to properly install the language servers. If you see any issues with the installation, make sure that the above are available in your path.

## Terminal

### Quick Codex question

Press **Ctrl+b c** to open a window named `question` at the end of the current
tmux session and launch Codex in the current pane's directory. The name appears
in the tmux navigation picker. Exit Codex when done;
the window closes and tmux returns to another window in the session.
Use **Ctrl+b w** to open a regular shell window.

### Tmux window search

This is a general tmux navigation tool; it works without an LLM. Coding-agent
hooks optionally record branch history, and associations can also be added manually.

The navigation helper and its tests live in `tmux_config/navigation/`.
`setup.sh` links that directory to `~/.tmux/navigation/`; notification
hooks call the helper there to record branch history.

Press **Ctrl+;** in WezTerm (or **Ctrl+b o** in any terminal) for a borderless picker
that fills the terminal and searches windows across all tmux sessions. Each window appears once; selecting it returns
to its active pane. Type a window name, repository, or branch;
use Up/Down to choose and Enter to jump directly to the window. Escape cancels.
Aligned, color-coded columns show the window, window location, process, repository,
ownership, recorded PR numbers, and branches with space between rows. Each row
combines recorded PRs and branches from the window’s panes. Windows are sorted
by their most recent visit. Focus hooks record visits; background output does
not change the order. Windows without visit history follow visited windows in
their existing order. Reload the tmux config to begin recording visits. Search
still ranks by match quality, with recent order breaking ties.
The bottom detail panel shows full paths
and branch/PR associations; Ctrl+/ toggles it. Ctrl+D opens a compact dropdown of known
repositories, with window counts and an **All repositories** option. Type to fuzzy
filter the list, use Up/Down to choose, and press Enter to select a repository.
Escape or Ctrl+C cancels. The main window/branch/PR query is preserved, and the
chosen repository filters by exact identity so similarly named repos stay separate.
Alt+O opens the highlighted window’s recorded PR links in Google Chrome and keeps
the picker open. A PR URL search opens only that PR. Windows without recorded PRs
show a message in the picker.
Automated review sessions named
`claude-pr-NUMBER-correctness/security/style` (and their `codex-pr-` equivalents)
are excluded, while ordinary development windows with review-related names stay visible.
Paste a full `https://github.com/OWNER/REPO/pull/NUMBER` URL to resolve its
source repository and branch automatically. Recorded PR URLs match locally without
contacting GitHub. Other successful PR lookups are cached for five minutes under
`$XDG_CACHE_HOME/agent-notify/prs` (default `~/.cache/agent-notify/prs`); lookup failures
remain retryable. Matching panes appear in the list;
press Enter to select one. Missing history and API errors appear in the picker,
and clearing the URL restores ordinary fuzzy search. Multiple matching panes remain
available to choose from. When the destination session is already displayed
in WezTerm, selection focuses its existing tab and pane. If the current terminal
is WezTerm but no tab displays that session, selection opens a new tab attached
to the same tmux server and session, leaving the original tab intact. Detaching
returns that new tab to your configured interactive login shell; exiting that
shell closes the tab. Without WezTerm, the current tmux client switches to the destination. The popup closes
and redraws before routing, and routing commands cannot read terminal input. Unrecorded, uncached URLs require authenticated `gh` access;
ordinary window/branch search filters the cached list live in fzf, without a typing
delay or Python filtering process. Exact branch claims retain ownership precedence. The picker requires Python 3.9+ and
fzf with interactive reload and preview support (tested with fzf 0.70 and tmux 3.6a).

The OWNER column distinguishes an explicit `claimed` branch/worktree from an
`observed` checkout. Hooks and picker seeding only observe directories; they do
not establish that every pane sharing a checkout owns its current branch. Once a
pane has explicit claims, incidental branch observations are hidden from its
navigation history. PR URLs and exact branch searches prefer explicit claims
over observations. Multiple genuine claims remain selectable, with their full
worktree paths and optional agent session IDs in the detail panel.

For a new task, create a dedicated worktree and claim it for the agent’s pane:

```sh
python3 ~/.tmux/navigation/search.py start eq/feat/example \
  --checkout ../repo-worktrees/example --base origin/main
```

Run from the repository and choose the base according to that repository’s
instructions. `start` creates a new branch from the base, or checks out an
existing local branch, without changing the shared checkout. It does not move
an agent’s working directory: use the returned worktree path for subsequent
commands. A branch already checked out elsewhere is rejected by Git.

For an existing isolated worktree, claim its current branch and then its PR:

```sh
python3 ~/.tmux/navigation/search.py claim --checkout ../repo-worktrees/example
python3 ~/.tmux/navigation/search.py claim https://github.com/OWNER/REPO/pull/123 \
  --checkout ../repo-worktrees/example
```

Claims validate that the worktree is on the requested branch. They retain the
canonical worktree root, branch, PR URL, and agent session ID when available.
Outside the target tmux pane, pass its known stable `--pane %ID`; never guess a
pane from whichever client happens to be active. Agents outside tmux have no
picker destination and should create worktrees with Git directly.

To explicitly backfill earlier work whose branch is no longer checked out, use
`link` from its repository with a branch name or PR URL:

```sh
python3 ~/.tmux/navigation/search.py link eq/feat/earlier-branch --pane %ID
python3 ~/.tmux/navigation/search.py link https://github.com/OWNER/REPO/pull/123 --pane %ID
```

History ends when the pane/server closes and is not restored by tmux-resurrect.
Existing agents are not relocated or assigned ownership automatically. Work
performed using shell `cd` or `git -C` without a corresponding hook directory
can still need an explicit claim or historical link.

Validate with `python3 -m unittest discover -s tmux_config/navigation -p 'test_*.py'`.
The terminal integration check, `python3 tmux_config/navigation/integration_test.py`,
uses a separate tmux server and a stub GitHub response.
Run `python3 tmux_config/navigation/detach_integration_test.py` to verify that
new tabs return to a usable shell after detach and close on explicit shell exit.

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

### Display focus with Hammerspoon

`mac_installs.sh` installs Hammerspoon with `brew install --cask hammerspoon`.
`setup.sh` links the Hammerspoon config to `~/.hammerspoon/init.lua` and adds the
Karabiner display-focus rule to the complex-modification assets. Existing configs
are preserved; if you already have a Hammerspoon init file, incorporate
`hammerspoon_config/init.lua` into it instead.

1. Open Hammerspoon and grant it **System Settings → Privacy & Security → Accessibility** permission.
2. Enable **Launch Hammerspoon at login** in Hammerspoon preferences, and use **Reload Config** after changing the Lua config.
3. In Karabiner **Complex Modifications**, enable **Command-Shift-K/J focus the display above/below (Hammerspoon)**.
4. Arrange your displays vertically in macOS **System Settings → Displays → Arrange**.

**Command-Shift-K** focuses the display above; **Command-Shift-J** focuses the
display below. Each shortcut activates the frontmost standard window on that
display, so you can immediately use app shortcuts such as Chrome's **Command-L**.
The pointer moves to the destination display's center so macOS Space-navigation
shortcuts (Command-Shift-H/L in this setup) also target that display. Windows stay
in place. With no adjacent display or eligible
window, focus stays where it is. These shortcuts override app bindings for the
same key combinations while the rule is enabled.

Karabiner sends F18/F19 to Hammerspoon, so keep those keys free of other bindings.
Hammerspoon must be running. Window selection uses
[`hs.window.orderedWindows()`](https://www.hammerspoon.org/docs/hs.window.html#orderedWindows)
and is limited to visible windows in the current Spaces; it does not switch Spaces
or restore minimized/hidden windows. Direction follows
[`hs.screen`](https://www.hammerspoon.org/docs/hs.screen.html#toNorth)'s display
geometry, excluding displays entirely to the left or right.

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

Treesitter installs syntax highlighting for the application and infrastructure
languages used in `~/corridor/core`, including Bash, YAML, JSON, TOML,
HCL/Terraform, Dockerfiles, Makefiles, CSS, HTML/XML, and Go templates.
Open Neovim after updating the config and allow parser installation to finish;
reopen the file if it was opened before its parser finished installing.

Markdown files use [render-markdown.nvim](https://github.com/MeanderingProgrammer/render-markdown.nvim)
to style headings, lists, tables, and code blocks inside the editor. Press
`Space m r` (or run `:RenderMarkdown buf_toggle`) to toggle rendering for the
current buffer. Insert mode shows the source for editing. Use
`:RenderMarkdown preview` for a rendered view beside the source.

Markdown link navigation uses [Marksman](https://github.com/artempyanykh/marksman),
installed automatically by Mason. With the cursor on a local Markdown link, press
`gd` to preview its target, then Enter to open it. In `:Review`'s working-tree
pane, `gd` opens the target in the separate browsing window. Use `Ctrl-O` to
return after a normal jump, or `Ctrl-W p` to return from the review browsing window.
After updating this config, restart Neovim and let Mason finish installing
Marksman. Existing sessions can install it with `:MasonInstall marksman`, then
run `:lua vim.lsp.enable('marksman')` and reopen the Markdown buffer.
For a Git worktree, add an empty `.marksman.toml` at the worktree root so Marksman
recognizes it as a project; its Git detection expects a `.git` directory.

```
curl -LO --output-dir ~/ https://github.com/neovim/neovim/releases/download/nightly/nvim-macos.tar.gz
tar xzf ~/nvim-macos.tar.gz
```

#### Markdown diagram previews

Neovim uses [md-render.nvim](https://github.com/delphinus/md-render.nvim) to
preview Markdown with Mermaid and PlantUML diagrams inside the editor.
Requires Neovim 0.12+ and a terminal supporting the Kitty graphics protocol;
the plugin documents testing on WezTerm, Kitty, and Ghostty. Both diagram
formats are handled by this single plugin inside Markdown previews.

Install the local renderers, then run `:Lazy sync` in Neovim:

```sh
brew install plantuml graphviz
npm install -g @mermaid-js/mermaid-cli
```

Open [the sample Markdown file](nvim_config/examples/diagrams.md), then use:

- `:MdRender` or `<leader>mp` for a floating preview.
- `:MdRender tab` or `<leader>mt` for a preview tab.
- `:vertical MdRender split` or `<leader>ms` for source and preview together.
- `:MdRender toggle` to switch the current window between source and preview.

Both `mermaid` and `plantuml` fenced blocks render locally. PlantUML stays as
source text if its renderer is missing. For the first test, use Neovim directly
in a WezTerm pane: tmux can filter graphics escape sequences, and passthrough
alone does not guarantee the plugin's output will reach the terminal.
This plugin is disabled in VS Code Neovim.

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
