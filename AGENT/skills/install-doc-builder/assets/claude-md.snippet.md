<!-- doc-index:guide:start -->
## Documentation index (`00-index.md`)

This repo keeps an auto-generated index of its docs. **Never hand-edit any
`00-index.md`** — it is rebuilt from frontmatter by `update_doc_index.py` (run via
`.claude/hooks/run-doc-index.sh`), on every `.md` write and at commit time. Editing it
is blocked by a deny rule.

- **Authored docs**: add YAML frontmatter — `title`, `summary`, `read_if`, and optional
  `created` (dated docs sort first). These become the index row.
- **Scan root / index path**: set in `.docbuild.config.yaml` (`root`, optional `index`).
- **Excluded automatically**: git submodules and anything in `.gitignore` — don't relist.
- **Extra exclusions**: add patterns (gitignore syntax) to `.indexbuilderignore` at the docs root.
- **Vendored/generated docs** that can't carry frontmatter: register them in
  `.indexbuilderinclude.yaml` (`path`, `title`, `summary`, `read_if`, optional `created`)
  instead of editing the file. When you find such a doc worth surfacing, add it there.
<!-- doc-index:guide:end -->
