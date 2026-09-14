-- Focus is intentionally changed only in response to a display-navigation hotkey.
local function focusScreen(direction)
    local focusedWindow = hs.window.focusedWindow()
    local currentScreen = focusedWindow and focusedWindow:screen() or hs.screen.mainScreen()
    if not currentScreen then
        return
    end

    local targetScreen
    if direction == "up" then
        targetScreen = currentScreen:toNorth(nil, true)
    else
        targetScreen = currentScreen:toSouth(nil, true)
    end
    if not targetScreen then
        return
    end

    -- Front-to-back ordering picks the topmost normal window on the target display.
    -- Standard-window filtering excludes Chrome status bars and other auxiliary UI.
    for _, window in ipairs(hs.window.orderedWindows()) do
        local screen = window:screen()
        if window:isStandard() and screen and screen:id() == targetScreen:id() then
            window:focus()
            return
        end
    end
end

-- Karabiner translates Cmd-Shift-K/J to these otherwise unused function keys.
hs.hotkey.bind({}, "F18", function()
    focusScreen("up")
end)
hs.hotkey.bind({}, "F19", function()
    focusScreen("down")
end)
