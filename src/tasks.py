import invoke


@invoke.task
def hello(ctx: invoke.Context):
    """A simple hello world task."""
    print("Hello, world!")
