--[[
References:
https://wezfurlong.org/wezterm/config/files.html
https://wezfurlong.org/wezterm/config/keys.html
https://wezfurlong.org/wezterm/config/default-keys.html
https://wezfurlong.org/wezterm/config/lua/general.html
]]

local wezterm = require("wezterm")
local mux = wezterm.mux
local act = wezterm.action

local config = {}

-- In newer versions of wezterm, use the config_builder which will
-- help provide clearer error messages
if wezterm.config_builder then
    config = wezterm.config_builder()
end

-- wezterm.on("gui-startup", function(cmd)
-- 	local tab, pane, window = mux.spawn_window(cmd or {})
-- 	pane:split({ size = 0.3 })
-- end)

config.inactive_pane_hsb = {
    saturation = 0.8,
    brightness = 0.5,
}

config.scrollback_lines = 20000
config.enable_scroll_bar = true

-- Cmd-click must bypass tmux mouse reporting before it can open a link.
config.bypass_mouse_reporting_modifiers = "CMD"

config.mouse_bindings = {
    -- tmux handles ordinary mouse interactions, so reserve Command-click for links.
    {
        event = { Up = { streak = 1, button = "Left" } },
        mods = "CMD",
        action = act.OpenLinkAtMouseCursor,
    },
    {
        event = { Down = { streak = 1, button = "Left" } },
        mods = "CMD",
        action = act.Nop,
    },
}

-- Send tmux's default prefix before a key so WezTerm shortcuts affect tmux.
local function send_tmux_prefix_key(key)
    return act.Multiple({
        act.SendKey({ key = "b", mods = "CTRL" }),
        act.SendKey({ key = key, mods = "NONE" }),
    })
end

config.keys = {
    -- Karabiner maps Option-B/F to Option-Left/Right globally. Translate those
    -- arrows into the Meta-B/F sequences that shell line editors use for words.
    {
        key = "LeftArrow",
        mods = "OPT",
        action = act.SendKey({ key = "b", mods = "ALT" }),
    },
    {
        key = "RightArrow",
        mods = "OPT",
        action = act.SendKey({ key = "f", mods = "ALT" }),
    },
    {
        key = "l",
        mods = "SUPER",
        action = wezterm.action.ActivatePaneDirection("Right"),
    },
    {
        key = "h",
        mods = "SUPER",
        action = wezterm.action.ActivatePaneDirection("Left"),
    },
    {
        key = "j",
        mods = "SUPER",
        action = wezterm.action.ActivatePaneDirection("Down"),
    },
    {
        key = "k",
        mods = "SUPER",
        action = wezterm.action.ActivatePaneDirection("Up"),
    },
    -- note: the standard wezterm convention for splits is opposite that of vim
    {
        key = "v",
        mods = "SUPER|SHIFT",
        action = wezterm.action.SplitHorizontal({ domain = "CurrentPaneDomain" }),
    },
    {
        key = "s",
        mods = "SUPER|SHIFT",
        action = wezterm.action.SplitVertical({ domain = "CurrentPaneDomain" }),
    },

    {
        key = "l",
        mods = "SUPER|CTRL",
        action = wezterm.action.AdjustPaneSize({ "Right", 5 }),
    },
    {
        key = "h",
        mods = "SUPER|CTRL",
        action = wezterm.action.AdjustPaneSize({ "Left", 5 }),
    },
    {
        key = "j",
        mods = "SUPER|CTRL",
        action = wezterm.action.AdjustPaneSize({ "Down", 5 }),
    },
    {
        key = "k",
        mods = "SUPER|CTRL",
        action = wezterm.action.AdjustPaneSize({ "Up", 5 }),
    },
    {
        key = "l",
        mods = "OPT|SHIFT",
        action = send_tmux_prefix_key("RightArrow"),
    },
    {
        key = "h",
        mods = "OPT|SHIFT",
        action = send_tmux_prefix_key("LeftArrow"),
    },
    {
        key = "j",
        mods = "OPT|SHIFT",
        action = send_tmux_prefix_key("DownArrow"),
    },
    {
        key = "k",
        mods = "OPT|SHIFT",
        action = send_tmux_prefix_key("UpArrow"),
    },
    {
        key = "o",
        mods = "SUPER",
        action = send_tmux_prefix_key("o"),
    },
    {
        key = "\\",
        mods = "SUPER|CTRL",
        action = wezterm.action.AdjustPaneSize({ "Right", 100 }),
    },
    {
        key = "r",
        mods = "CMD",
        action = act.PromptInputLine({
            description = "Enter new name for tab",
            action = wezterm.action_callback(function(window, _, line)
                -- A nil value means the rename prompt was cancelled.
                if line then
                    window:active_tab():set_title(line)
                end
            end),
        }),
    },
    {
        key = "r",
        mods = "CMD|SHIFT",
        action = wezterm.action.ReloadConfiguration,
    },
}

return config
