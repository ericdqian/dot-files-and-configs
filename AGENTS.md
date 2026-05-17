Make frequent commmits for what would be considered atomic units of work.

Before you return control to the user, if you have new commits, push. If no PR exists yet, make one. Make the PR description using the /prepare-pr skill

When the user asks you to revise something you already did, or gives guidance that sounds like a reusable principle, ask whether they would like that feedback persisted into an `AGENTS.md` file for future agents.

Scope `AGENTS.md` files to the directory where the guidance applies. Generic agent behavior and cross-repo preferences belong in this root `AGENTS.md`, which is symlinked into the global agent locations. Repo-specific instructions should live in that repo's `AGENTS.md`, and directory- or subsystem-specific instructions should live in the deepest relevant directory so only the right files inherit them. Do not duplicate narrow instructions in broader files unless the broader file needs to point agents to where the narrower guidance lives.
