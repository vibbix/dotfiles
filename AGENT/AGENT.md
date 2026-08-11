# Vibbix's AGENT file
 - `vibbix/dotfile` contains my dotfiles, used for preferences across a multitude of applications and processes
# Preferences
## Shell
I tend to always use `zsh` for my shell, so take extra care when writing shell commands to make sure they're compatible.
i.e. particularly for dealing with word splits.
### Language Servers (LSP)
Always prefer using an LSP for code navigation and edits when one is available for the language at hand. If no LSP is available, warn me before falling back to text-based search/edits.
## Inline comments
Save history for the git commits (or wiki pages); comments should be for explaining quirky behavior - not for explaining how something came to be.
Assume all code is self-documenting, and only write comments when necessary. Clean-up as you go if you see comments in the area
where you are working that do not fit this new objective. You are allowed to explain non-obvious *why*, not *what*.
Do not narrate steps or restate the code. A fast and loose rule is that most file "headers" are only 4 lines of text, roughly a paragrapy, and that at most, most source files are 5-10% comments.
Anything above that is seen as an LLM smell.

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
```
### Recommended Libraries
These are my "usual" libaries, that I tend to use in every project of mine
 - [tqdm](https://pypi.org/project/tqdm/) - used as a "wrapper" for python iterators to give live feed
 - [sourcetypes3](https://pypi.org/project/sourcetypes3/) - Used for syntax highlighting of inline languages in python
 - [requests](https://pypi.org/project/requests/) and [requests-cache](https://pypi.org/project/requests-cache/) - For making HTTP calls, and caching them locally
 - [pillow](https://pypi.org/project/Pillow/) - image manipulation
 - [beautifulsoup](https://www.crummy.com/software/BeautifulSoup/) - used for parsing HTML (in the future, maybe i should explore [scrapy](https://www.scrapy.org/))
## Javascript/Typescript Projects
### Conventions
#### Date types
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