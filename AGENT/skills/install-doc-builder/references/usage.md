# Doc-index builder: ignore, include, and config files

`update_doc_index.py` scans a docs root recursively for `*.md`, reads each file's
frontmatter, and writes a table into `00-index.md` between the
`<!-- doc-index:start -->` and `<!-- doc-index:end -->` markers. It only rewrites that
block; the rest of `00-index.md` is left alone.

## Frontmatter (authored docs)

Docs you control should carry frontmatter. These columns drive the table:

```yaml
---
title: docs/claude/01-architecture.md   # display text (path by convention)
summary: One-line "what is it".
read_if: When you should open this doc.
created: 2026-06-19                      # dated docs sort first, ascending
---
```

## Defaults you don't configure

Git submodules (paths in `.gitmodules`) and anything matched by `.gitignore` are
skipped. You don't need to repeat either in `.indexbuilderignore`.

## `.indexbuilderignore`

Optional. Gitignore syntax, placed at the docs root, for exclusions beyond git's own
(drafts, scratch files, and the like). Don't create an empty one; add the file only when
you have patterns to list:

```
drafts/
**/SCRATCH.md
```

## `.indexbuilderinclude.{json,yaml,yml}`

Optional. Use it for docs that **cannot carry frontmatter**, such as vendored, generated,
or read-only files. Create it only when there's something to register. List entries under
`files:` (it also accepts `include:` or `includes:`). Each entry needs a `path` relative
to the include file; the other keys mirror the frontmatter. An include entry overrides an
auto-discovered doc at the same path.

```yaml
files:
  - path: vendor/third-party/README.md
    title: Third-party library overview
    summary: How the bundled vendor library is structured.
    read_if: You need to touch anything under vendor/.
    created: 2026-06-19
```

When you find a vendored doc worth surfacing, add it here rather than editing the file.

## `.docbuild.config.{json,yaml,yml}`

Optional, and only needed when the docs root isn't the default `docs/claude`. The script
finds it by walking up from the working directory to the git root. Recognized keys:

- `root`: directory to scan, relative to the config file.
- `index`: explicit index path (default `<root>/00-index.md`).

CLI arguments (the `root` positional and `--index`) override the config. With no config
and no CLI args, the scan root is `<git-root>/docs/claude`.

```yaml
root: docs
# index: docs/00-index.md
```

## Running it

```bash
.claude/hooks/run-doc-index.sh          # rebuild the index
.claude/hooks/run-doc-index.sh --check  # exit non-zero if stale (pre-commit)
```
