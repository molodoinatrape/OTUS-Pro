"""
TODO:

foo should accept a dict argument, both keys and values are string.
"""


def foo(x: dict[str, str]):
    pass

foo({"foo": "bar"})
foo({"foo": 1})  # pyright: ignore[reportArgumentType]
