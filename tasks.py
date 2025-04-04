from src.tasks import *


@invoke.task
def build(ctx: invoke.Context):
    # example output: 123abc
    if result := ctx.run("git rev-parse --short HEAD"):
        hash: str = result.stdout.strip()

    # Turns `git@github.com:coilysiren/backend.git` into `coilysiren/backend`
    if result := ctx.run("git config --get remote.origin.url"):
        repo: str = result.stdout.strip()
        repo = repo.split(":")[-1].split(".")[0]

    # example output: coilysiren/backend:123abc
    tag = f"{repo}:{hash}"

    ctx.run(f"docker build -t {tag} .", echo=True)
