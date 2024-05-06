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

config.keys = {
    -- Clears the scrollback and viewport, and then sends CTRL-L to ask the
    -- shell to redraw its prompt
    {
        key = "k",
        mods = "SUPER",
        action = act.Multiple({
            act.ClearScrollback("ScrollbackAndViewport"),
            act.SendKey({ key = "L", mods = "CTRL" }),
        }),
    },
    {
        key = "l",
        mods = "SUPER|SHIFT",
        action = wezterm.action.ActivatePaneDirection("Right"),
    },
    {
        key = "h",
        mods = "SUPER|SHIFT",
        action = wezterm.action.ActivatePaneDirection("Left"),
    },
    {
        key = "j",
        mods = "SUPER|SHIFT",
        action = wezterm.action.ActivatePaneDirection("Down"),
    },
    {
        key = "k",
        mods = "SUPER|SHIFT",
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
        mods = "SUPER|CTRL",
        action = wezterm.action.AdjustPaneSize({ "Right", 5 }),
    },
    {
        key = "\\",
        mods = "SUPER|CTRL",
        action = wezterm.action.AdjustPaneSize({ "Right", 100 }),
    },
    {
        key = "r",
        mods = "CMD|SHIFT",
        action = wezterm.action.ReloadConfiguration,
    },
}

return config
