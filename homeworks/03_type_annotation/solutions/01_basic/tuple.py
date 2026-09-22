"""
TODO:

foo should accept a tuple argument, 1st item is a string, 2nd item is an integer.
"""


def foo(x: tuple[str, int]):
    pass

foo(("foo", 1))

foo((1, 2))  # pyright: ignore[reportArgumentType]
foo(("foo", "bar"))  # pyright: ignore[reportArgumentType]
foo((1, "foo"))  # pyright: ignore[reportArgumentType]
