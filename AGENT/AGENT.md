# Vibbix's AGENT file
 - `vibbix/dotfile` contains my dotfiles, used for preferences across a multitude of applications and processes
# Preferences
## Inline comments
Keep comments sparse. Match the surrounding code's density; explain non-obvious *why*, not *what*. Do not narrate steps or restate the code.
## Python Projects
### Prefer `uv` over `python`
Always prefer to use `uv`/`uvx` over `python`/`pipx`.
When asked to write new scripts, unless told otherwise, use [PEP 723 - Intline script metadata](https://peps.python.org/pep-0723/).

For example:
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pexpect<=4.9.0",
# ]
# ///
# PYTHON CODE HERE
```### Prefer `uv` over `python`
Always prefer to use `uv`/`uvx` over `python`/`pipx`.
When asked to write new scripts, unless told otherwise, use [PEP 723 - Intline script metadata](https://peps.python.org/pep-0723/).

For example:
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pexpect<=4.9.0",
# ]
# ///
# PYTHON CODE HERE
```
## Javascript/Typescript Projects
### Conventions
- Use Temporal types (`Temporal.Instant`, `Temporal.ZonedDateTime`, `Temporal.Duration`) in schemas and domain types; convert to ISO strings only at the wire boundary
### Greenfield projects
New "web", or web-adjacent project will use the `bun` runtime.
Ask these questions when we start a new project:
1. Will this project require complicated serve patterns?
 - This will determine if we have a `serve.ts` instead of a 
2. Will this be a Single Page Application(`SPA`) or a Multi-Page Application (`MPA`)?
 - this will determine if the `bun dev` command will be `bun --watch pages/index.html` or `bun --watch pages/*/**.html` if the answer to question 1 is "no".

<!-- When bun introduces assett handling, a third question will be introduced -->
### Bun Preferences for SPA's
When usimg `bun`, let's have our projects prefer to use a `index.html` serving strategy like as seen in [their documentation](https://bun.com/docs/bundler/html-static) and [building here](https://bun.com/docs/bundler/standalone-html). Create a default `index.html`  that looks like this:

```html
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>My App</title>
    <link rel="stylesheet" href="./src/styles.css" />
  </head>
  <body>
    <div id="root"></div>
    <script src="./app.tsx"></script>
  </body>
</html>
```

and a `src/app.tsx` that looks like this:

```typescript
import React, { useState } from "react";
import { createRoot } from "react-dom/client";

function App() {
  return (
    <main>
      <h1>Single-file React App</h1>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
```

and a empty `./src/styles.css`,

## Git
### Branch names
The preferred naming scheme for branches is `[feature|bugfix]/[JIRA-TICKET]-[feature-name-kebab-case]-[optional-version-number]`
i.e. `feature/SI-13197-get-okta-working-v3`
## Github / Software Forges
### Creating PR's
Have a short description, 2-3 sentences to describe the change. Under that, have a `What's changed` section, with single bullets per feature/change, consisting of around 3 to 5 words (max 7).

For headline description, YOU MUST use the "[humanizer](https://github.com/blader/humanizer)" skill thats installed on the PR text, to reduce verbosity. 

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

