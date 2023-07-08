local M = {}

function M.setup()
	local leap = require("leap")
	leap.set_default_keymaps()
	leap.opts.safe_labels = {}
	leap.init_highlight(true)
end

return M
