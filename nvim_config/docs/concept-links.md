# Concept links in Markdown

Marksman definition navigation (including the navigator's `gd` preview) falls
back to resolving links such as
`[source](concept://owner/repo/src/example.lua#L12)` when Marksman returns no
location. The first two segments identify the repository; the remaining path is
relative to its root. Percent-encoded paths are supported. An omitted anchor
opens line 1; `#L12` opens line 12.

The resolver reads the nearest `.concept-links.json` at or above the Markdown
document's directory. If that file maps the repository key to an existing
directory, it uses that checkout. Otherwise it uses
`~/learning/repositories.json`. Both files use this shape:

```json
{
  "repositories": {
    "owner/repo": "~/projects/repo"
  }
}
```

Only the nearest override is consulted; mappings in more distant overrides are
not merged. A removed override checkout falls back to the registry.

If the selected checkout lacks the file, the resolver runs `git show` in the
**registry** checkout. For run documents, the nearest ancestor `revision.json`
provides `head`, provided its `pr` identifies the linked repository
(`owner/repo/123`). A run's commit is never used for a different repository.
Outside a run, a document may supply a hexadecimal commit in YAML front matter:

```markdown
---
verified_at: "0123456789abcdef0123456789abcdef01234567"
---
```

Historical content opens at the cited line in a read-only, unmodifiable scratch
buffer with the source file type. No checkout files are written. Unknown keys,
missing revision metadata, and unavailable commits or files produce warnings
when the fallback is needed. Existing files always open from the selected
checkout; the resolver does not translate line numbers after source changes.

## Tests

From the repository root, with the Markdown Tree-sitter parsers installed:

```sh
nvim --headless -u NONE -i NONE -l nvim_config/tests/concept_links.lua
nvim --headless -u NONE -i NONE -l nvim_config/tests/markdown_lsp.lua
```

The second test also requires the installed Marksman and nv-navigator plugins.
The resolver test uses temporary Git repositories and a temporary home directory
for its registry, leaving the real registry unchanged.
