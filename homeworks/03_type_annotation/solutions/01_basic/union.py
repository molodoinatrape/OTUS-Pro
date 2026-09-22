"""
TODO:

foo should accept a argument that's either a string or integer.
"""


def foo(x: str | int):
    pass

foo("foo")
foo(1)

foo([])  # pyright: ignore[reportArgumentType]
