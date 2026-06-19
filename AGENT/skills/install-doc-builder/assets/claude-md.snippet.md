<!-- doc-index:guide:start -->
## Documentation index (`00-index.md`)

This repo keeps an auto-generated index of its docs. **Never hand-edit any
`00-index.md`.** It is rebuilt from frontmatter by `update_doc_index.py` (run via
`.claude/hooks/run-doc-index.sh`) on every `.md` write and at commit time. A
`permissions.deny` rule in `.claude/settings.json` blocks edits to it.

- **Authored docs**: add YAML frontmatter (`title`, `summary`, `read_if`, and optional
  `created`). Dated docs sort first; same-date ties break by filename. These become the row.
- **Scan root**: defaults to `docs/claude`. To use another folder, add a
  `.docbuild.config.yaml` at the repo root with `root:` (and optional `index:`).
- **Excluded automatically**: git submodules and anything in `.gitignore`. Don't relist them.
- **Extra exclusions** (optional): create `.indexbuilderignore` at the docs root with
  gitignore-syntax patterns. There may be no such file; add one only when you need it.
- **Vendored or generated docs** that can't carry frontmatter (optional): register them in
  `.indexbuilderinclude.yaml` at the docs root (`path`, `title`, `summary`, `read_if`,
  optional `created`) instead of editing the file. Create the file when you first need it.
<!-- doc-index:guide:end -->
