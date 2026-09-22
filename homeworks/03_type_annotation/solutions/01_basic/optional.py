"""
TODO:

foo can accept an integer argument, None or no argument at all.
"""


def foo(x: int | None = None):
    pass

foo(10)
foo(None)
foo()

foo("10")  # expect-type-error
