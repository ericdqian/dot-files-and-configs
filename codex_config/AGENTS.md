`codex_config/config.toml` is symlinked to `/etc/codex/config.toml` (system-level config), not to `~/.codex/config.toml`. Codex's config precedence is project `.codex/config.toml` > profile > `~/.codex/config.toml` (user) > `/etc/codex/config.toml` (system) > built-in defaults, so anything in `~/.codex/config.toml` silently overrides this file on a matching key.

`~/.codex/config.toml` itself stays a real, local-only file — it is not tracked or symlinked, and `setup.sh` deliberately leaves it alone.

When adding or changing a Codex setting:
- If it's a deliberate, portable preference with no absolute path in it (e.g. `approval_policy`, `sandbox_mode`, `personality`, plugin enablement), add it here in `codex_config/config.toml`.
- If it contains an absolute path (`notify`, `mcp_servers.*`, `marketplaces.*.source`, `desktop.open-in-target-preferences.perPath`), is a per-project `trust_level` entry, or is account/session state the Codex app manages itself, put it directly in `~/.codex/config.toml` instead — do not add it here.
- `model` / `model_reasoning_effort` belong in `~/.codex/config.toml`: the Codex app rewrites these directly on every model switch, and has been observed to prune the rest of the file down to just these two keys on write. Don't rely on it preserving anything you put in `~/.codex/config.toml` beyond what it actively manages — that's exactly why the durable settings above live in the system-level file instead.

Caveat: `/etc/codex/config.toml` applies to every user account on the machine, not just this one.
