## Deploy reference

Before touching any deploy config (Dockerfile, Makefile, `deploy/main.yml`,
`.github/workflows/build-and-publish.yml`, or the Tailscale/k3s secrets),
read
[`coilysiren/infrastructure/docs/k3s-deploy-notes.md`](../infrastructure/docs/k3s-deploy-notes.md).
That doc captures the four-repo accumulated knowledge of the homelab
deploy rig (topology, SSM/GH-secret layout, canonical manifest/workflow
shapes, every trap we've hit, setup checklist, triage tree). When you
resolve a new pitfall, add it there — don't scatter fixes across each
repo's notes.

## File Access

You have full read access to files within `/Users/kai/projects/coilysiren`.

## Autonomy

- Run tests after every change without asking.
- Fix lint errors automatically.
- If tests fail, debug and fix without asking.
- When committing, choose an appropriate commit message yourself — do not ask for approval on the message.
- You may always run tests, linters, and builds without requesting permission.
- Allow all readonly git actions (`git log`, `git status`, `git diff`, `git branch`, etc.) without asking.
- Allow `cd` into any `/Users/kai/projects/coilysiren` folder without asking.
- Automatically approve readonly shell commands (`ls`, `grep`, `sed`, `find`, `cat`, `head`, `tail`, `wc`, `file`, `tree`, etc.) without asking.
- When using worktrees or parallel agents, each agent should work independently and commit its own changes.
- Do not open pull requests unless explicitly asked.

## Git workflow

Commit directly to `main` without asking for confirmation, including `git add`. Do not open pull requests unless explicitly asked.

Commit whenever a unit of work feels sufficiently complete — after fixing a bug, adding a feature, passing tests, or reaching any other natural stopping point. Don't wait for the user to ask.
