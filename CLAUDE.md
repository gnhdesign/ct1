# CT1 coffee table

Parametric coffee table models: `ct1.py` (CadQuery), `ct1_solidcraft.py` and `ct3_solidcraft.py`
(built in a running SolidCraft app through `sc.py`, its MCP client). Outputs go to `build/`,
which is gitignored.

## Keep the repo free of personal data

This is a public repository. Before every commit, check the staged changes and keep out:

- Local paths: user folders (`C:\Users\...`, `/home/...`), AppData, scratch or temp folders, and
  non-standard install locations. Code finds tools through environment variables, `PATH` or
  standard install folders, and paths relative to the repo.
- Tokens, keys and passwords, such as the SolidCraft control token. Code may read them at run
  time from the environment or the app's token file, but never stores or prints them.
- Email addresses, machine names, usernames and other details about the machine or account.
- Generated files from `build/` (renders and screenshots show the local desktop) and anything
  else covered by `.gitignore`.

The author's name in copyright headers, the `LICENSE`, and the links to the published project
page in the README are intentional and stay.

A quick check before committing:

``` bash
git diff --cached | grep -n -i -E 'C:\\\\Users|/home/|AppData|token=|password|@[a-z0-9-]+\.[a-z]{2,}'
```
