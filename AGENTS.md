# Agent instructions

See `../AGENTS.md` for workspace-level conventions (git workflow, test/lint autonomy, readonly ops, writing voice, deploy knowledge). This file covers only what's specific to this repo.

---

Deploy config (Dockerfile, Makefile, `deploy/main.yml`, `.github/workflows/build-and-publish.yml`, Tailscale/k3s secrets) follows the canonical homelab rig documented in [`infrastructure/docs/k3s-deploy-notes.md`](../infrastructure/docs/k3s-deploy-notes.md). When you resolve a new pitfall, add it there, not here.
