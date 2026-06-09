Make frequent commmits for what would be considered atomic units of work.

Before you return control to the user, if you have new commits, push. If no PR exists yet, make one. Make the PR description using the /prepare-pr skill. Keep the PR title and description updated so they accurately reflect the current status and scope of the PR as it evolves.

Opened PR branches should use the format `eq/<type>/<description>`, such as `eq/chore/update-install-scripts`, where `<type>` is `feat`, `bug`, or `chore` depending on the PR's purpose. Use `feat` for features, `bug` for fixes, and `chore` for scripts, maintenance, or other changes that do not add real product functionality.

When the user asks you to revise something you already did, or gives guidance that sounds like a reusable principle, ask whether they would like that feedback persisted into an `AGENTS.md` file for future agents.

Function and method ordering:
- Order code for the reader's path through the file.
- Put each top-level function or method before the helpers that serve it.
- Put those helpers immediately after that top-level function or method.
- Then move on to the next top-level function or method and its helpers.
- For a class that handles a business entity's lifecycle, order its methods by the sequence they are normally invoked in, such as create/setup methods first, then update/transition methods, then completion/archive/delete methods.
- For example, if top-level function `A` uses helpers `a` and `b`, and top-level function `B` uses helpers `c` and `d`, prefer this order: `A`, `a`, `b`, `B`, `c`, `d`.

Scope `AGENTS.md` files to the directory where the guidance applies. Generic agent behavior and cross-repo preferences belong in this root `AGENTS.md`, which is symlinked into the global agent locations. Repo-specific instructions should live in that repo's `AGENTS.md`, and directory- or subsystem-specific instructions should live in the deepest relevant directory so only the right files inherit them. If a repo-specific rule reveals a broader reusable principle, that generalized principle may be added to this root `AGENTS.md` while the concrete repo-specific rule stays in the relevant repo or directory. Do not duplicate narrow instructions in broader files unless the broader file needs to point agents to where the narrower guidance lives.
